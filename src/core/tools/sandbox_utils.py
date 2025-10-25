# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Sandbox Utilities for Chroot Isolation.

This module provides utilities for creating and managing chroot sandboxes
for secure shell command execution in RL environments.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


class SandboxManager:
    """
    Manages chroot sandbox creation and initialization.

    This class handles creating minimal chroot environments with only
    essential binaries, keeping package managers separate for security.
    """

    # Core binaries that should always be available in sandbox
    CORE_BINARIES = [
        "bash",
        "sh",
        "ls",
        "cat",
        "cp",
        "mv",
        "rm",
        "mkdir",
        "rmdir",
        "chmod",
        "chown",
        "echo",
        "pwd",
        "cd",
        "touch",
        "grep",
        "sed",
        "awk",
        "find",
        "head",
        "tail",
        "wc",
        "sort",
        "uniq",
        "cut",
        "tr",
    ]

    # Package managers and network tools (kept separate)
    PACKAGE_MANAGERS = [
        "curl",
        "wget",
        "git",
        "apt",
        "apt-get",
        "pip",
        "pip3",
        "npm",
        "yarn",
    ]

    def __init__(self, sandbox_root: str):
        """
        Initialize sandbox manager.

        Args:
            sandbox_root: Root path where sandbox will be created
        """
        self.sandbox_root = Path(sandbox_root)

    def create_sandbox(
        self,
        include_package_managers: bool = False,
        init_commands: Optional[List[str]] = None,
    ) -> bool:
        """
        Create a minimal chroot sandbox.

        Args:
            include_package_managers: If True, package managers are available in sandbox.
                                     If False, they're in /tools/ and must be copied manually.
            init_commands: List of shell commands to run during initialization

        Returns:
            True if successful, False otherwise

        Example:
            >>> manager = SandboxManager("/tmp/sandbox_123")
            >>> manager.create_sandbox(
            ...     include_package_managers=False,
            ...     init_commands=["git clone ...", "cd workspace"]
            ... )
        """
        try:
            # Create directory structure
            self._create_directory_structure()

            # Copy essential binaries
            self._copy_binaries(self.CORE_BINARIES, target_dir="bin")

            # Handle package managers
            if include_package_managers:
                self._copy_binaries(self.PACKAGE_MANAGERS, target_dir="usr/bin")
            else:
                # Put them in /tools/ for manual opt-in
                self._copy_binaries(self.PACKAGE_MANAGERS, target_dir="tools")

            # Copy required shared libraries
            self._copy_libraries()

            # Create workspace directory
            (self.sandbox_root / "workspace").mkdir(exist_ok=True)

            # Run init commands if provided
            if init_commands:
                self._run_init_commands(init_commands)

            return True

        except Exception as e:
            print(f"Error creating sandbox: {e}")
            return False

    def _create_directory_structure(self):
        """Create the basic chroot directory structure."""
        directories = [
            "bin",
            "usr/bin",
            "usr/lib",
            "usr/lib64",
            "lib",
            "lib64",
            "tmp",
            "workspace",
            "tools",
            "etc",
            "dev",
            "proc",
        ]

        for directory in directories:
            (self.sandbox_root / directory).mkdir(parents=True, exist_ok=True)

        # Make tmp writable
        os.chmod(self.sandbox_root / "tmp", 0o1777)

    def _copy_binaries(self, binaries: List[str], target_dir: str):
        """
        Copy binaries to sandbox.

        Args:
            binaries: List of binary names to copy
            target_dir: Target directory relative to sandbox root (e.g., "bin" or "tools")
        """
        target_path = self.sandbox_root / target_dir

        for binary in binaries:
            # Find binary on host system
            try:
                result = subprocess.run(
                    ["which", binary],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0:
                    source_path = result.stdout.strip()
                    if source_path and os.path.exists(source_path):
                        dest_path = target_path / os.path.basename(source_path)
                        shutil.copy2(source_path, dest_path)
                        # Make executable
                        os.chmod(dest_path, 0o755)

            except Exception as e:
                # Skip binaries that don't exist - not critical
                print(f"Warning: Could not copy {binary}: {e}")
                continue

    def _copy_libraries(self):
        """
        Copy required shared libraries for binaries.

        This uses ldd to find dependencies and copies them to the sandbox.
        """
        # Find all binaries we copied
        bin_dirs = [
            self.sandbox_root / "bin",
            self.sandbox_root / "usr/bin",
            self.sandbox_root / "tools",
        ]

        libraries_copied = set()

        for bin_dir in bin_dirs:
            if not bin_dir.exists():
                continue

            for binary in bin_dir.iterdir():
                if binary.is_file():
                    self._copy_binary_dependencies(binary, libraries_copied)

    def _copy_binary_dependencies(self, binary_path: Path, libraries_copied: set):
        """
        Copy shared library dependencies for a specific binary.

        Args:
            binary_path: Path to the binary
            libraries_copied: Set of already copied libraries (to avoid duplicates)
        """
        try:
            # Run ldd to find dependencies
            result = subprocess.run(
                ["ldd", str(binary_path)],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return

            # Parse ldd output
            for line in result.stdout.splitlines():
                # Look for lines like: libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6
                parts = line.strip().split()
                if len(parts) >= 3 and "=>" in parts:
                    lib_path = parts[2]
                    if lib_path.startswith("/") and os.path.exists(lib_path):
                        if lib_path not in libraries_copied:
                            self._copy_library(lib_path)
                            libraries_copied.add(lib_path)

        except Exception as e:
            print(f"Warning: Could not copy dependencies for {binary_path}: {e}")

    def _copy_library(self, lib_path: str):
        """
        Copy a single library to the sandbox.

        Args:
            lib_path: Full path to the library on host system
        """
        try:
            # Determine target directory (lib or lib64)
            if "lib64" in lib_path:
                target_dir = self.sandbox_root / "lib64"
            else:
                target_dir = self.sandbox_root / "lib"

            target_dir.mkdir(parents=True, exist_ok=True)

            # Copy library
            dest_path = target_dir / os.path.basename(lib_path)
            if not dest_path.exists():
                shutil.copy2(lib_path, dest_path)

            # Also check /usr/lib and /usr/lib64
            if "/usr/" in lib_path:
                if "lib64" in lib_path:
                    usr_target_dir = self.sandbox_root / "usr/lib64"
                else:
                    usr_target_dir = self.sandbox_root / "usr/lib"

                usr_target_dir.mkdir(parents=True, exist_ok=True)
                usr_dest_path = usr_target_dir / os.path.basename(lib_path)
                if not usr_dest_path.exists():
                    shutil.copy2(lib_path, usr_dest_path)

        except Exception as e:
            print(f"Warning: Could not copy library {lib_path}: {e}")

    def _run_init_commands(self, commands: List[str]):
        """
        Run initialization commands inside the chroot.

        Args:
            commands: List of shell commands to execute
        """
        for command in commands:
            try:
                # Run command inside chroot
                full_command = (
                    f"chroot {self.sandbox_root} /bin/bash -c {repr(command)}"
                )

                subprocess.run(
                    full_command,
                    shell=True,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )

            except Exception as e:
                print(f"Warning: Init command failed: {command}: {e}")

    def cleanup(self):
        """Remove the sandbox directory."""
        try:
            if self.sandbox_root.exists():
                shutil.rmtree(self.sandbox_root)
                return True
        except Exception as e:
            print(f"Error cleaning up sandbox: {e}")
            return False

    def get_chroot_path(self) -> str:
        """Get the chroot path as a string."""
        return str(self.sandbox_root)


def create_sandbox(
    sandbox_root: str,
    include_package_managers: bool = False,
    init_commands: Optional[List[str]] = None,
) -> Optional[str]:
    """
    Convenience function to create a sandbox.

    Args:
        sandbox_root: Root path for sandbox
        include_package_managers: Whether to include package managers in sandbox
        init_commands: List of init commands to run

    Returns:
        Path to sandbox if successful, None otherwise

    Example:
        >>> sandbox_path = create_sandbox(
        ...     "/tmp/sandbox_123",
        ...     include_package_managers=False,
        ...     init_commands=["mkdir /workspace/project"]
        ... )
    """
    manager = SandboxManager(sandbox_root)
    if manager.create_sandbox(include_package_managers, init_commands):
        return manager.get_chroot_path()
    return None
