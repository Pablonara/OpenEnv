# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Python Code Action Environment.

This module provides a server-side environment implementation for executing
Python code actions using PyExecutor.
"""

import uuid
import os

from core.env_server import Action, Environment, Observation
from core.tools import PyExecutor, ShellExecutor, SandboxManager

from ..models import CodeAction, ShellAction, CodeObservation, CodeState, SandboxConfig
from .transforms import create_safe_coding_transform


class PythonCodeActEnv(Environment):
    """
    Python Code Action Environment for executing code and tracking state.

    This environment executes Python code submitted as CodeAction during step,
    maintains the last exit code in its state, and returns results wrapped
    in CodeObservation.

    Args:
        transform: Optional transform to apply to observations
        additional_imports: List of additional module imports to authorize
                          (e.g., ["numpy", "pandas", "matplotlib"])

    Example:
        >>> env = PythonCodeActEnv()
        >>> obs = env.reset()
        >>> action = CodeAction(code="print('Hello, World!')")
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "Hello, World!\n"
        >>> print(obs.exit_code)  # 0
        >>> print(env.state.last_exit_code)  # 0
    """

    def __init__(
        self,
        sandbox_config: SandboxConfig = None,
    ):
        self.sandbox_config = sandbox_config or SandboxConfig()
        self.transform = create_safe_coding_transform()
        self._executor = PyExecutor()
        self._shell_executor = ShellExecutor()
        self._sandbox_manager = None
        self._state = CodeState()

    def reset(self) -> Observation:
        """
        Reset environment and start fresh execution session.

        Returns:
            Initial observation with empty stdout/stderr and exit_code=0
        """
        # Clean up old sandbox if exists
        if self._sandbox_manager:
            self._sandbox_manager.cleanup()

        # Initialize fresh state
        self._state = CodeState(episode_id=str(uuid.uuid4()), step_count=0)
        # Add last_exit_code to state
        self._state.last_exit_code = 0

        # Reset executor to clear any previously defined variables/functions
        self._executor = PyExecutor()

        # Create new sandbox if enabled
        chroot_path = None
        if self.sandbox_config.enable:
            sandbox_root = f"/tmp/sandbox_{self._state.episode_id}"
            self._sandbox_manager = SandboxManager(sandbox_root)

            if self._sandbox_manager.create_sandbox(
                include_package_managers=self.sandbox_config.include_package_managers,
                init_commands=self.sandbox_config.init_commands,
            ):
                chroot_path = self._sandbox_manager.get_chroot_path()
            else:
                # Sandbox creation failed, log warning
                print(f"Warning: Failed to create sandbox, running without chroot")

        # Reset shell executor with chroot if available
        self._shell_executor = ShellExecutor(chroot_path=chroot_path)

        # Reset transform to clear any accumulated state
        self.transform = create_safe_coding_transform()

        # Return initial observation
        observation = CodeObservation(
            stdout="",
            stderr="",
            exit_code=0,
        )

        return self._apply_transform(observation)

    def step(self, action: Action) -> Observation:
        """
        Execute code action and return observation.

        Args:
            action: CodeAction containing the code to execute

        Returns:
            CodeObservation with execution results (stdout, stderr, exit_code)

        Raises:
            ValueError: If action is not a CodeAction instance
        """
        if not isinstance(action, CodeAction):
            raise ValueError(f"Expected CodeAction, got {type(action)}")

        # Execute the code using PyExecutor
        result = self._executor.run(action.code)

        # Update state
        self._state.step_count += 1
        self._state.last_exit_code = result.exit_code

        # Create observation from execution result
        observation = CodeObservation(
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
        )

        return self._apply_transform(observation)

    @property
    def state(self) -> CodeState:
        """Get current environment state including last exit code."""
        return self._state
