# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Python Chroot Action Environment.

This module provides a server-side environment implementation for executing
commands in a chroot sandbox. The environment:
1. Copies a target directory to a temporary location
2. Symlinks system binaries into the chroot for command execution
3. Executes commands within the sandboxed environment
"""

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from core.env_server import Action, Environment, Observation

from ..models import ChrootAction, ChrootObservation, ChrootState
from .transforms import create_safe_chroot_transform


class PythonChrootEnv(Environment):
    """
    Python Chroot Action Environment for executing commands in a sandboxed environment.

    This environment sets up a chroot sandbox by:
    - Copying a target directory to a temporary location
    - Creating symlinks to system binaries (from /bin, /usr/bin, etc.)
    - Executing commands within this sandboxed environment
    - Maintaining execution state and exit codes

    Args:
        target_dir: Directory to copy into the chroot sandbox
        symlink_dirs: List of system directories to symlink into chroot
                     (default: ['/bin', '/usr/bin', '/usr/local/bin'])
        transform: Optional transform to apply to observations
        shell: Shell to use for command execution (default: '/bin/bash')

    Example:
        >>> env = PythonChrootEnv(target_dir="/path/to/project")
        >>> obs = env.reset()
        >>> action = ChrootAction(command="ls -la")
        >>> obs = env.step(action)
        >>> print(obs.stdout)
        >>> print(obs.exit_code)
    """

    def __init__(
        self,
        target_dir: Optional[str] = None,
        symlink_dirs: Optional[list[str]] = None,
        shell: str = "/bin/bash",
    ):
        self.target_dir = target_dir or "/tmp/default_target"
        self.symlink_dirs = symlink_dirs or ["/bin", "/usr/bin", "/usr/local/bin"]
        self.shell = shell
        self.transform = create_safe_chroot_transform()
        self._state = ChrootState()
        self._chroot_path: Optional[Path] = None

    def _setup_chroot(self) -> Path:
        """
        Set up the chroot environment:
        1. Create temporary directory
        2. Copy target_dir into it
        3. Symlink system binaries

        Returns:
            Path to the chroot directory
        """
        # Create temporary directory for chroot
        temp_dir = tempfile.mkdtemp(prefix="openenv_chroot_")
        chroot_path = Path(temp_dir)

        try:
            # Copy target directory into chroot
            if os.path.exists(self.target_dir):
                target_name = os.path.basename(self.target_dir.rstrip("/"))
                dest_path = chroot_path / target_name
                shutil.copytree(self.target_dir, dest_path)
            else:
                # If target doesn't exist, create basic directory structure
                (chroot_path / "home").mkdir(exist_ok=True)

            # Create lib directories for symlinks
            (chroot_path / "bin").mkdir(exist_ok=True)
            (chroot_path / "usr" / "bin").mkdir(parents=True, exist_ok=True)
            (chroot_path / "usr" / "local" / "bin").mkdir(parents=True, exist_ok=True)
            (chroot_path / "lib").mkdir(exist_ok=True)
            (chroot_path / "lib64").mkdir(exist_ok=True)
            (chroot_path / "usr" / "lib").mkdir(parents=True, exist_ok=True)

            # Symlink system binaries
            for sys_dir in self.symlink_dirs:
                sys_path = Path(sys_dir)
                if sys_path.exists():
                    for binary in sys_path.iterdir():
                        try:
                            link_path = chroot_path / binary.name
                            # Create symlink (skip if already exists)
                            if not link_path.exists():
                                link_path.symlink_to(binary)
                        except (OSError, PermissionError):
                            # Skip binaries that can't be symlinked
                            pass

            # Symlink essential library directories
            for lib_dir in ["/lib", "/lib64", "/usr/lib"]:
                lib_path = Path(lib_dir)
                if lib_path.exists():
                    link_name = lib_path.name
                    link_path = chroot_path / link_name
                    try:
                        if not link_path.exists() and not link_path.is_symlink():
                            link_path.symlink_to(lib_path)
                    except (OSError, PermissionError):
                        pass

        except Exception as e:
            # Clean up on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"Failed to setup chroot: {e}")

        return chroot_path

    def _cleanup_chroot(self) -> None:
        """Clean up the chroot environment."""
        if self._chroot_path and self._chroot_path.exists():
            try:
                shutil.rmtree(self._chroot_path)
            except Exception as e:
                print(f"Warning: Failed to cleanup chroot: {e}")
            self._chroot_path = None

    def reset(self) -> Observation:
        """
        Reset environment and set up fresh chroot sandbox.

        Returns:
            Initial observation with empty stdout/stderr and exit_code=0
        """
        # Clean up old chroot if it exists
        self._cleanup_chroot()

        # Set up new chroot
        self._chroot_path = self._setup_chroot()

        # Initialize fresh state
        self._state = ChrootState(episode_id=str(uuid.uuid4()), step_count=0)
        self._state.last_exit_code = 0

        # Reset transform
        self.transform = create_safe_chroot_transform()

        # Return initial observation
        observation = ChrootObservation(
            stdout="",
            stderr="",
            exit_code=0,
        )

        return self._apply_transform(observation)

    def step(self, action: Action) -> Observation:
        """
        Execute command action in chroot sandbox and return observation.

        Args:
            action: ChrootAction containing the command to execute

        Returns:
            ChrootObservation with execution results (stdout, stderr, exit_code)

        Raises:
            ValueError: If action is not a ChrootAction instance
            RuntimeError: If chroot is not initialized
        """
        if not isinstance(action, ChrootAction):
            raise ValueError(f"Expected ChrootAction, got {type(action)}")

        if not self._chroot_path:
            raise RuntimeError("Chroot environment not initialized. Call reset() first.")

        # Execute command in chroot
        try:
            result = subprocess.run(
                [self.shell, "-c", action.command],
                cwd=str(self._chroot_path),
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = "Command execution timed out after 30 seconds"
            exit_code = 124
        except Exception as e:
            stdout = ""
            stderr = f"Error executing command: {str(e)}"
            exit_code = 1

        # Update state
        self._state.step_count += 1
        self._state.last_exit_code = exit_code

        # Create observation
        observation = ChrootObservation(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
        )

        return self._apply_transform(observation)

    @property
    def state(self) -> ChrootState:
        """Get current environment state including last exit code."""
        return self._state

    def __del__(self):
        """Clean up chroot on deletion."""
        self._cleanup_chroot()
