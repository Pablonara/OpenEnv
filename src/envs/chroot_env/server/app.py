# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
FastAPI application for the Chroot Environment.

This module creates an HTTP server that exposes the PythonChrootEnv
over HTTP endpoints, making it compatible with HTTPEnvClient.

Usage:
    # Development (with auto-reload):
    uvicorn envs.chroot_env.server.app:app --reload --host 0.0.0.0 --port 8000

    # Production:
    uvicorn envs.chroot_env.server.app:app --host 0.0.0.0 --port 8000 --workers 4

    # Or run directly:
    python -m envs.chroot_env.server.app

Environment variables:
    TARGET_DIR: Directory to copy into chroot (default: /tmp/default_target)
    SYMLINK_DIRS: Comma-separated list of system dirs to symlink (default: /bin,/usr/bin,/usr/local/bin)
    SHELL: Shell to use for command execution (default: /bin/bash)
"""

import os

from core.env_server import create_app

from ..models import ChrootAction, ChrootObservation
from .python_chroot_env import PythonChrootEnv

# Get configuration from environment variables
target_dir = os.getenv("TARGET_DIR", "/tmp/default_target")
symlink_dirs_str = os.getenv("SYMLINK_DIRS", "/bin,/usr/bin,/usr/local/bin")
symlink_dirs = [d.strip() for d in symlink_dirs_str.split(",")]
shell = os.getenv("SHELL", "/bin/bash")

# Create the environment instance
env = PythonChrootEnv(
    target_dir=target_dir,
    symlink_dirs=symlink_dirs,
    shell=shell,
)

# Create the app with web interface and README integration
app = create_app(env, ChrootAction, ChrootObservation, env_name="chroot_env")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
