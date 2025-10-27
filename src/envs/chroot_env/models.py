"""
envs/chroot_env/models.py
--------------------------------
Action/Observation types for the Chroot environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.env_server import Action, Observation, State


@dataclass
class ChrootAction(Action):
    """
    Represents a single command execution request in a chroot environment.
    """

    command: str
    # Optional: future fields like 'timeout_s': float, 'env_vars': dict, etc.


@dataclass
class ChrootObservation(Observation):
    """
    Result of executing a command in the chroot environment.
    """

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


@dataclass
class ChrootState(State):
    """State for Chroot environment with persistent execution context."""

    last_exit_code: int = 0
