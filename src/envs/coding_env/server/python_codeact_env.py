# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Python Code Action Environment.

This module provides a server-side environment implementation for executing
Python code actions using PyExecutor and shell commands using ShellExecutor.
"""

import uuid

from core.env_server import Action, Environment, Observation
from core.tools import PyExecutor, ShellExecutor

from ..models import CodeAction, ShellAction, CodeObservation, CodeState
from .transforms import create_safe_coding_transform


class PythonCodeActEnv(Environment):
    """
    Python Code Action Environment for executing code and tracking state.

    This environment executes Python code (CodeAction) or shell commands
    (ShellAction) during step, maintains the last exit code in its state,
    and returns results wrapped in CodeObservation.

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
        >>>
        >>> # Shell command example
        >>> action = ShellAction(command="echo 'Hello from shell'")
        >>> obs = env.step(action)
        >>> print(obs.stdout)  # "Hello from shell\n"
    """

    def __init__(
        self,
    ):
        self.transform = create_safe_coding_transform()
        self._executor = PyExecutor()
        self._shell_executor = ShellExecutor()
        self._state = CodeState()

    def reset(self) -> Observation:
        """
        Reset environment and start fresh execution session.

        Returns:
            Initial observation with empty stdout/stderr and exit_code=0
        """
        # Initialize fresh state
        self._state = CodeState(episode_id=str(uuid.uuid4()), step_count=0)
        # Add last_exit_code to state
        self._state.last_exit_code = 0

        # Reset executor to clear any previously defined variables/functions
        self._executor = PyExecutor()

        # Reset shell executor
        self._shell_executor = ShellExecutor()

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
        Execute code or shell action and return observation.

        Args:
            action: CodeAction (Python code) or ShellAction (shell command)

        Returns:
            CodeObservation with execution results (stdout, stderr, exit_code)

        Raises:
            ValueError: If action is not a CodeAction or ShellAction instance
        """
        if isinstance(action, CodeAction):
            # Execute Python code using PyExecutor
            result = self._executor.run(action.code)

        elif isinstance(action, ShellAction):
            # Execute shell command using ShellExecutor
            # Create a new executor with the specified timeout
            shell_exec = ShellExecutor(timeout=action.timeout)
            result = shell_exec.run(action.command)

        else:
            raise ValueError(f"Expected CodeAction or ShellAction, got {type(action)}")

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
