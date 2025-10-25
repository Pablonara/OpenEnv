# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Shell Command Executor.

This module provides functionality for executing shell commands safely in a
subprocess and capturing the results.
"""

import subprocess
from typing import Optional

from core.env_server.types import CodeExecResult


class ShellExecutor:
    """
    Executor for running shell commands in a subprocess.

    This class provides a simple interface to execute shell commands and
    capture the results including stdout, stderr, and exit code.

    Args:
        timeout: Maximum time in seconds to allow command to run (default: 30)
        shell: Whether to run command through the shell (default: True)
        cwd: Working directory for command execution (default: None = current directory)

    Example:
        >>> # Basic usage
        >>> executor = ShellExecutor()
        >>> result = executor.run("echo 'Hello, World!'")
        >>> print(result.stdout)  # "Hello, World!\n"
        >>> print(result.exit_code)  # 0
        >>>
        >>> # With timeout
        >>> executor = ShellExecutor(timeout=5)
        >>> result = executor.run("sleep 10")  # Will timeout
        >>> print(result.exit_code)  # 1
        >>> print(result.stderr)  # Contains timeout error
        >>>
        >>> # List files
        >>> result = executor.run("ls -la")
        >>> print(result.stdout)  # Directory listing
    """

    def __init__(
        self,
        timeout: int = 30,
        shell: bool = True,
        cwd: Optional[str] = None,
    ):
        """
        Initialize the ShellExecutor.

        Args:
            timeout: Maximum seconds to wait for command completion (default: 30)
            shell: Whether to execute through shell (default: True)
            cwd: Working directory path (default: None)
        """
        self.timeout = timeout
        self.shell = shell
        self.cwd = cwd

    def run(self, command: str) -> CodeExecResult:
        """
        Execute a shell command and return the result.

        Args:
            command: Shell command string to execute

        Returns:
            CodeExecResult containing stdout, stderr, and exit_code

        Example:
            >>> executor = ShellExecutor()
            >>> result = executor.run("echo 'test'")
            >>> print(result.stdout)  # "test\n"
            >>> print(result.exit_code)  # 0
            >>>
            >>> # Error handling
            >>> result = executor.run("nonexistent_command")
            >>> print(result.exit_code)  # Non-zero
            >>> print(result.stderr)  # Contains error message
        """
        try:
            # Execute the command using subprocess
            process = subprocess.Popen(
                command,
                shell=self.shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                exit_code = process.returncode

                return CodeExecResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                )

            except subprocess.TimeoutExpired:
                # Kill the process if it times out
                process.kill()
                stdout, stderr = process.communicate()

                return CodeExecResult(
                    stdout=stdout,
                    stderr=f"Command timed out after {self.timeout} seconds\n{stderr}",
                    exit_code=124,  # Standard timeout exit code
                )

        except Exception as e:
            # Catch any other errors (e.g., command parsing issues)
            return CodeExecResult(
                stdout="",
                stderr=f"Shell execution error: {str(e)}",
                exit_code=1,
            )
