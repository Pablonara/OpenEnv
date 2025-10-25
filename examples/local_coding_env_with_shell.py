# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

#!/usr/bin/env python3
"""
Example showing CodingEnv with shell command execution support.

This demonstrates how to execute both Python code and shell commands
in the same environment.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from envs.coding_env import CodeAction, ShellAction, CodingEnv


def main():
    """Test CodingEnv with shell command support."""
    print("=" * 60)
    print("CodingEnv with Shell Command Support")
    print("=" * 60)
    print()

    try:
        # Create client from Docker image
        print("Creating client from Docker image...")
        print("  CodingEnv.from_docker_image('coding-env:latest')")
        print()

        client = CodingEnv.from_docker_image("coding-env:latest")

        print("✓ Client created and container started!\n")

        # Reset
        print("1. Reset Environment:")
        print("-" * 60)
        result = client.reset()
        print(f"   stdout: {result.observation.stdout}")
        print(f"   exit_code: {result.observation.exit_code}")

        state = client.state()
        print(f"   State: episode_id={state.episode_id}, step_count={state.step_count}")

        # Execute shell commands
        print("\n2. Execute Shell Commands:")
        print("-" * 60)

        shell_samples = [
            ("List files", "ls -la"),
            ("Check directory", "pwd"),
            ("Echo message", "echo 'Hello from shell!'"),
            ("Date", "date"),
            ("System info", "uname -a"),
        ]

        for i, (description, command) in enumerate(shell_samples, 1):
            result = client.step(ShellAction(command=command))
            print(f"   {i}. {description}")
            print(f"      Command: {command}")
            print(f"      → stdout: {result.observation.stdout.strip()[:100]}...")
            print(f"      → exit_code: {result.observation.exit_code}")

        # Mix Python and Shell
        print("\n3. Mix Python Code and Shell Commands:")
        print("-" * 60)

        # Python: Create a variable
        print("   1. Python: Create variable")
        result = client.step(CodeAction(code="x = 42\nprint(f'x = {x}')"))
        print(f"      → stdout: {result.observation.stdout.strip()}")

        # Shell: Create a temp file
        print("   2. Shell: Create temp file")
        result = client.step(ShellAction(command="echo 'test data' > /tmp/test.txt"))
        print(f"      → exit_code: {result.observation.exit_code}")

        # Shell: Read the file
        print("   3. Shell: Read temp file")
        result = client.step(ShellAction(command="cat /tmp/test.txt"))
        print(f"      → stdout: {result.observation.stdout.strip()}")

        # Python: Use the variable from step 1
        print("   4. Python: Use variable from step 1")
        result = client.step(CodeAction(code="print(f'x squared = {x * x}')"))
        print(f"      → stdout: {result.observation.stdout.strip()}")

        # Shell: File operations
        print("\n4. Shell: File Operations:")
        print("-" * 60)

        operations = [
            ("Create directory", "mkdir -p /tmp/test_dir"),
            ("Create file", "echo 'content' > /tmp/test_dir/file.txt"),
            ("List directory", "ls -l /tmp/test_dir"),
            ("Read file", "cat /tmp/test_dir/file.txt"),
            ("Remove file", "rm /tmp/test_dir/file.txt"),
            ("Remove directory", "rmdir /tmp/test_dir"),
        ]

        for i, (description, command) in enumerate(operations, 1):
            result = client.step(ShellAction(command=command))
            print(f"   {i}. {description}")
            if result.observation.stdout.strip():
                print(f"      → stdout: {result.observation.stdout.strip()}")
            print(f"      → exit_code: {result.observation.exit_code}")

        # Test error handling with shell commands
        print("\n5. Shell Command Error Handling:")
        print("-" * 60)

        error_samples = [
            ("Nonexistent command", "nonexistent_command"),
            ("Permission denied", "cat /etc/shadow"),
            ("Invalid option", "ls --invalid-option"),
        ]

        for i, (description, command) in enumerate(error_samples, 1):
            result = client.step(ShellAction(command=command))
            print(f"   {i}. {description}")
            print(f"      Command: {command}")
            print(f"      → exit_code: {result.observation.exit_code}")
            if result.observation.stderr:
                error_msg = result.observation.stderr[:80]
                if len(result.observation.stderr) > 80:
                    error_msg += "..."
                print(f"      → stderr: {error_msg}")

        # Test timeout
        print("\n6. Shell Command with Timeout:")
        print("-" * 60)

        print("   1. Quick command (no timeout)")
        result = client.step(ShellAction(command="sleep 1 && echo 'done'", timeout=5))
        print(f"      → stdout: {result.observation.stdout.strip()}")
        print(f"      → exit_code: {result.observation.exit_code}")

        print("   2. Long command (will timeout)")
        result = client.step(ShellAction(command="sleep 10", timeout=2))
        print(f"      → exit_code: {result.observation.exit_code}")
        if result.observation.stderr:
            print(f"      → stderr: {result.observation.stderr[:60]}...")

        # Check final state
        print("\n7. Check Final State:")
        print("-" * 60)
        state = client.state()
        print(f"   episode_id: {state.episode_id}")
        print(f"   step_count: {state.step_count}")
        print(f"   last_exit_code: {state.last_exit_code}")

        print("\n" + "-" * 60)
        print("\n✓ All operations successful!")
        print()

        print("Cleaning up...")
        client.close()
        print("✓ Container stopped and removed")
        print()

        print("=" * 60)
        print("Test completed successfully! 🎉")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
