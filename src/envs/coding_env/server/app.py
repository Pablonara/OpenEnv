# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Coding Environment.

This module creates an HTTP server that exposes the PythonCodeActEnv
over HTTP endpoints, making it compatible with HTTPEnvClient.

Usage:
    # Development (with auto-reload):
    uvicorn envs.coding_env.server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn envs.coding_env.server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m envs.coding_env.server.app
"""

from typing import Any, Dict

from fastapi import FastAPI
from core.env_server import HTTPEnvServer
from core.env_server.types import Action

from ..models import CodeAction, ShellAction, CodeObservation
from .python_codeact_env import PythonCodeActEnv


class CodingEnvHTTPServer(HTTPEnvServer):
    """Custom HTTP server that handles both CodeAction and ShellAction."""

    def _deserialize_action(self, action_data: Dict[str, Any]) -> Action:
        """
        Deserialize action data into either CodeAction or ShellAction.

        Args:
            action_data: Dictionary containing action data

        Returns:
            CodeAction or ShellAction instance based on payload content
        """
        # Remove metadata if present (it will be set via kw_only field)
        metadata = action_data.pop("metadata", {})

        # Detect action type based on fields present
        if "code" in action_data:
            # It's a CodeAction
            action = CodeAction(code=action_data["code"])
        elif "command" in action_data:
            # It's a ShellAction
            timeout = action_data.get("timeout", 30)
            action = ShellAction(command=action_data["command"], timeout=timeout)
        else:
            raise ValueError(
                f"Unknown action type. Expected 'code' or 'command' in action data, got: {list(action_data.keys())}"
            )

        action.metadata = metadata
        return action


# Create the environment instance
env = PythonCodeActEnv()

# Create FastAPI app
app = FastAPI(title="Coding Environment Server")

# Create custom server and register routes
server = CodingEnvHTTPServer(env, CodeAction, CodeObservation)
server.register_routes(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
