# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Transforms specific to chroot environments."""

import re

from core.env_server.base_transforms import CompositeTransform
from core.env_server.interfaces import Transform
from core.env_server.types import Observation

from ..models import ChrootObservation


class ChrootSafetyTransform(Transform):
    """Evaluates command safety and assigns penalties for dangerous patterns."""

    def __init__(self, penalty: float = -1.0):
        self.penalty = penalty
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Recursive delete from root
            r"mkfs",  # Filesystem formatting
            r"dd\s+if=/dev",  # Raw disk writes
            r":(){",  # Fork bomb
        ]

    def __call__(self, observation: Observation) -> Observation:
        if not isinstance(observation, ChrootObservation):
            return observation

        if "last_command" in observation.metadata:
            command = observation.metadata["last_command"]
            for pattern in self.dangerous_patterns:
                if re.search(pattern, command):
                    observation.reward = self.penalty
                    observation.metadata["safety_violation"] = pattern
                    break
            else:
                if observation.reward is None:
                    observation.reward = 0.0

        return observation


class ChrootExecutionTransform(Transform):
    """Evaluates execution success and rewards clean executions."""

    def __init__(self, success_bonus: float = 0.1, error_penalty: float = -0.1):
        self.success_bonus = success_bonus
        self.error_penalty = error_penalty

    def __call__(self, observation: Observation) -> Observation:
        if not isinstance(observation, ChrootObservation):
            return observation

        exec_score = 0.0

        # Reward successful execution (exit_code == 0)
        if observation.exit_code == 0:
            exec_score += self.success_bonus
        else:
            exec_score += self.error_penalty

        # Add to existing reward
        if observation.reward is None:
            observation.reward = exec_score
        else:
            observation.reward += exec_score

        return observation


def create_safe_chroot_transform() -> CompositeTransform:
    """Create a transform focused on safe command execution in chroot."""
    return CompositeTransform([ChrootSafetyTransform(), ChrootExecutionTransform()])
