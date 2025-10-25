"""
envs/coding_env/models.py
--------------------------------
Action/Observation types for the Coding environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, List

from core.env_server import Action, Observation, State


@dataclass
class SandboxConfig:
    """
    Configuration for chroot sandbox initialization.

    Args:
        enable: Whether to enable chroot sandboxing (default: True)
        init_commands: List of shell commands to run during sandbox initialization
                      (e.g., ["git clone https://...", "cd workspace"])
        include_package_managers: Whether to include curl/git/apt in sandbox
                                 If False, they're in /tools/ and must be explicitly copied
    """

    enable: bool = True
    init_commands: List[str] = field(default_factory=list)
    include_package_managers: bool = False


@dataclass
class CodeAction(Action):
    """
    Represents a single code execution request.
    """

    code: str
    # Optional: future fields like 'lint': bool, 'timeout_s': float, etc.


@dataclass
class ShellAction(Action):
    """
    Represents a single shell command execution request.
    """

    command: str
    timeout: int = 30  # Maximum seconds to wait for command completion


@dataclass
class CodeObservation(Observation):
    """
    Result of executing code in the environment.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


@dataclass
class CodeState(State):
    """State for CodeAct environment with persistent execution context."""

    last_exit_code: int = 0
