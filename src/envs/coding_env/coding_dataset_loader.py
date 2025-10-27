"""
coding_dataset_loader.py
--------------------------------
Dataset loader and chroot reset functionality for coding-traces integration.

This module provides utilities to load coding scenarios from dataset.json
and set up chroot jails pointing to specific subrepos in the coding-traces directory.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CodingScenario:
    """
    Represents a single coding scenario from the dataset.

    Attributes:
        instance_id: Unique identifier for the scenario
        repo: Repository name (format: owner__repo.commit)
        base_commit: Base commit hash (often empty in dataset)
        problem_statement: Description of the bug to fix
        patch: Git diff patch showing the correct fix
        test_patch: Test patch (often empty)
        hints_text: Optional hints
        created_at: Creation timestamp
        version: Version number
        PASS_TO_PASS: List of tests that should pass
        FAIL_TO_PASS: List of tests that should start failing then pass
        language: Programming language (e.g., "python")
        strategy: Strategy used to create the scenario
        cost: Cost metric
        explanation: Additional explanation
    """

    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    patch: str
    test_patch: str
    hints_text: str
    created_at: str
    version: int
    PASS_TO_PASS: List[str]
    FAIL_TO_PASS: List[str]
    language: str
    strategy: str
    cost: float
    explanation: str


class CodingDatasetManager:
    """
    Manages loading coding scenarios and setting up chroot environments.

    This class handles:
    1. Loading scenarios from dataset.json
    2. Finding corresponding subrepo directories in coding-traces
    3. Creating chroot jails with the appropriate repository
    """

    def __init__(
        self,
        dataset_path: str = "./dataset.json",
        coding_traces_root: str = "../coding-traces",
    ):
        """
        Initialize the dataset manager.

        Args:
            dataset_path: Path to dataset.json file
            coding_traces_root: Path to coding-traces repository root
        """
        self.dataset_path = Path(dataset_path)
        self.coding_traces_root = Path(coding_traces_root)
        self._scenarios = None

    def load_scenarios(
        self,
        limit: Optional[int] = None,
        shuffle: bool = False,
        seed: Optional[int] = None,
    ) -> List[CodingScenario]:
        """
        Load scenarios from dataset.json.

        Args:
            limit: Maximum number of scenarios to load
            shuffle: Whether to shuffle the scenarios
            seed: Random seed for shuffling

        Returns:
            List of CodingScenario objects
        """
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found at {self.dataset_path}")

        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        scenarios = [CodingScenario(**item) for item in data]

        if shuffle:
            import random

            if seed is not None:
                rng = random.Random(seed)
                rng.shuffle(scenarios)
            else:
                random.shuffle(scenarios)

        if limit is not None:
            scenarios = scenarios[:limit]

        self._scenarios = scenarios
        return scenarios

    def get_subrepo_path(self, scenario: CodingScenario) -> Path:
        """
        Get the path to the subrepo directory for a scenario.

        Args:
            scenario: CodingScenario object

        Returns:
            Path to the subrepo directory

        Raises:
            FileNotFoundError: If subrepo directory doesn't exist
        """
        # Structure: coding-traces/repo_name/instance_id/repo
        subrepo_path = (
            self.coding_traces_root / scenario.repo / scenario.instance_id / "repo"
        )

        if not subrepo_path.exists():
            raise FileNotFoundError(
                f"Subrepo not found at {subrepo_path}. "
                f"Expected structure: coding-traces/{scenario.repo}/{scenario.instance_id}/repo"
            )

        return subrepo_path

    def prepare_chroot_init_commands(
        self, scenario: CodingScenario, workspace_path: str = "/workspace"
    ) -> List[str]:
        """
        Prepare initialization commands for chroot sandbox.

        This creates commands that will:
        1. Copy the subrepo into the sandbox workspace
        2. Set proper permissions

        Args:
            scenario: CodingScenario object
            workspace_path: Path within chroot where code will be located

        Returns:
            List of shell commands to run during sandbox initialization
        """
        subrepo_path = self.get_subrepo_path(scenario)

        # Get absolute path for copying
        abs_subrepo_path = subrepo_path.resolve()

        commands = [
            f"mkdir -p {workspace_path}",
            # Note: The actual copying needs to happen before chroot
            # These are placeholder commands that run inside chroot
            f"cd {workspace_path}",
        ]

        return commands

    def setup_sandbox_workspace(
        self,
        scenario: CodingScenario,
        sandbox_root: Path,
        workspace_name: str = "workspace",
    ) -> Path:
        """
        Copy the subrepo into the sandbox before chrooting.

        This must be called BEFORE entering the chroot, as we need
        filesystem access to copy the repository files.

        Args:
            scenario: CodingScenario object
            sandbox_root: Root directory of the sandbox
            workspace_name: Name of workspace directory

        Returns:
            Path to workspace directory inside sandbox
        """
        subrepo_path = self.get_subrepo_path(scenario)
        workspace_path = sandbox_root / workspace_name

        # Create workspace directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Copy repository contents into workspace
        # Using shutil.copytree with dirs_exist_ok for clean copying
        try:
            # Copy all contents from subrepo into workspace
            for item in subrepo_path.iterdir():
                src = subrepo_path / item.name
                dst = workspace_path / item.name

                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst, symlinks=True)
                else:
                    shutil.copy2(src, dst)

            print(f"Copied repository from {subrepo_path} to {workspace_path}")

        except Exception as e:
            print(f"Error copying repository: {e}")
            raise

        return workspace_path


class CodingEnvResetManager:
    """
    Manages reset operations for coding environment with chroot isolation.

    This class integrates with OpenEnv's SandboxManager to create
    isolated environments for each coding scenario.
    """

    def __init__(self, dataset_manager: CodingDatasetManager):
        """
        Initialize the reset manager.

        Args:
            dataset_manager: CodingDatasetManager instance
        """
        self.dataset_manager = dataset_manager

    def prepare_reset_config(
        self,
        scenario: CodingScenario,
        sandbox_root: str,
        include_package_managers: bool = True,
    ) -> dict:
        """
        Prepare configuration for resetting environment with a scenario.

        Args:
            scenario: CodingScenario to set up
            sandbox_root: Root path for sandbox
            include_package_managers: Whether to include git/curl/apt in sandbox

        Returns:
            Dictionary with sandbox configuration
        """
        # Setup workspace before creating sandbox
        sandbox_path = Path(sandbox_root)
        self.dataset_manager.setup_sandbox_workspace(
            scenario, sandbox_path, workspace_name="workspace"
        )

        # Get init commands (these run inside chroot)
        init_commands = self.dataset_manager.prepare_chroot_init_commands(scenario)

        return {
            "sandbox_root": sandbox_root,
            "include_package_managers": include_package_managers,
            "init_commands": init_commands,
            "scenario": scenario,
            "workspace_path": "/workspace",  # Path inside chroot
        }


def load_scenarios_for_training(
    dataset_path: str = "./dataset.json",
    coding_traces_root: str = "../coding-traces",
    limit: Optional[int] = None,
    shuffle: bool = True,
    seed: Optional[int] = 42,
) -> tuple:
    """
    Convenience function to load scenarios for training.

    Args:
        dataset_path: Path to dataset.json
        coding_traces_root: Path to coding-traces repository
        limit: Maximum number of scenarios
        shuffle: Whether to shuffle scenarios
        seed: Random seed

    Returns:
        Tuple of (CodingDatasetManager, list of scenarios)
    """
    manager = CodingDatasetManager(dataset_path, coding_traces_root)
    scenarios = manager.load_scenarios(limit=limit, shuffle=shuffle, seed=seed)
    return manager, scenarios


# Example usage:
if __name__ == "__main__":
    # Load scenarios
    manager, scenarios = load_scenarios_for_training(
        dataset_path="./dataset.json",
        coding_traces_root="../coding-traces",
        limit=5,
        shuffle=True,
        seed=42,
    )

    print(f"Loaded {len(scenarios)} scenarios")

    # Example: prepare reset config for first scenario
    if scenarios:
        scenario = scenarios[0]
        print(f"\nScenario: {scenario.instance_id}")
        print(f"Repo: {scenario.repo}")
        print(f"Problem: {scenario.problem_statement[:100]}...")

        # Get subrepo path
        try:
            subrepo_path = manager.get_subrepo_path(scenario)
            print(f"Subrepo path: {subrepo_path}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
