"""
ChrootEnv
---------
Client-side wrapper for the Chroot environment.

Two usage modes:
1. Direct instantiation (no Docker/server required):
   >>> env = ChrootEnv(target_dir="/path/to/project")
   >>> result = env.reset()
   >>> result = env.step(ChrootAction(command="ls -la"))

2. HTTP client to a remote server:
   >>> env = ChrootEnv(base_url="http://localhost:8000")
   >>> result = env.reset()
   >>> result = env.step(ChrootAction(command="ls -la"))

3. Docker container mode:
   >>> env = ChrootEnv.from_docker_image("chroot-env:latest")
   >>> result = env.reset()
   >>> result = env.step(ChrootAction(command="ls -la"))
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Union

from core.client_types import StepResult
from core.env_server import Environment, Action
from core.http_env_client import HTTPEnvClient

from .models import ChrootAction, ChrootObservation, ChrootState

if TYPE_CHECKING:
    from core.containers.runtime import ContainerProvider


class ChrootEnv(HTTPEnvClient[ChrootAction, ChrootObservation]):
    """
    Chroot Environment Client supporting both direct and HTTP modes.

    This client can operate in two modes:
    1. Direct mode: Directly instantiate the environment server-side logic
    2. HTTP mode: Connect to a running HTTP server

    Args:
        base_url: HTTP server URL (for HTTP mode)
        target_dir: Directory to copy into chroot (for direct mode)
        symlink_dirs: System directories to symlink (for direct mode)
        shell: Shell to use for execution (for direct mode)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        target_dir: Optional[str] = None,
        symlink_dirs: Optional[list[str]] = None,
        shell: str = "/bin/bash",
    ):
        """
        Initialize ChrootEnv in either HTTP or direct mode.

        If base_url is provided, operates in HTTP mode.
        Otherwise, operates in direct mode with local environment.
        """
        if base_url:
            # HTTP mode
            super().__init__(base_url)
            self._direct_env = None
        else:
            # Direct mode - initialize the server-side environment locally
            from .server.python_chroot_env import PythonChrootEnv
            
            self._direct_env = PythonChrootEnv(
                target_dir=target_dir,
                symlink_dirs=symlink_dirs,
                shell=shell,
            )
            # Don't call parent init - we're not using HTTP
            self.base_url = None

    def reset(self) -> StepResult[ChrootObservation]:
        """Reset the environment."""
        if self._direct_env:
            obs = self._direct_env.reset()
            return StepResult(observation=obs, reward=None, done=False)
        else:
            return super().reset()

    def step(self, action: ChrootAction) -> StepResult[ChrootObservation]:
        """Execute a step in the environment."""
        if self._direct_env:
            obs = self._direct_env.step(action)
            return StepResult(observation=obs, reward=None, done=False)
        else:
            return super().step(action)

    def state(self) -> ChrootState:
        """Get current environment state."""
        if self._direct_env:
            return self._direct_env.state
        else:
            return super().state()

    def close(self) -> None:
        """Close the environment."""
        if self._direct_env:
            # Clean up direct environment
            if hasattr(self._direct_env, '_cleanup_chroot'):
                self._direct_env._cleanup_chroot()
        else:
            super().close()

    # --- HTTPEnvClient abstract hooks (for HTTP mode) ---

    def _step_payload(self, action: ChrootAction) -> dict:
        # Shape expected by the server's /step endpoint under "action"
        return {
            "command": action.command,
        }

    def _parse_result(self, payload: dict) -> StepResult[ChrootObservation]:
        # Expecting: { "observation": {...}, "reward": <float|null>, "done": <bool>, "info": {...} }
        obs = ChrootObservation(**payload["observation"])
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=bool(payload.get("done", False)),
        )

    def _parse_state(self, payload: dict) -> ChrootState:
        """
        Parse server response into ChrootState object.

        Args:
            payload: JSON response from /state endpoint

        Returns:
            ChrootState object with episode_id, step_count, and last_exit_code
        """
        return ChrootState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            last_exit_code=payload.get("last_exit_code", 0),
        )
