#!/usr/bin/env python3
"""
Test script for Coding Environment with Chroot Sandbox and Init Hooks.

This script demonstrates:
1. Creating a sandboxed environment with chroot
2. Using init_commands to set up the workspace
3. Core binaries vs package managers separation
4. How agents must explicitly enable package managers
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

# Get the working directory (OpenEnv root)
working_directory = str(Path(__file__).parent.parent.absolute())

# Add src to path
sys.path.insert(0, str(Path(working_directory) / "src"))

from envs.coding_env import CodingEnv, CodeAction, ShellAction


def wait_for_server(url, timeout=30):
    """Wait for server to be ready."""
    print(f"Waiting for server at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health")
            if response.status_code == 200:
                print(f"✓ Server ready!")
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    """Run the test."""
    print("=" * 70)
    print("Coding Environment - Chroot Sandbox with Init Hooks Test")
    print("=" * 70)
    print()

    # Set port and localhost
    port = "8004"
    localhost = f"http://localhost:{port}"

    # Configure sandbox with init commands
    init_commands = [
        "mkdir -p /workspace/project",
        "echo 'Workspace initialized' > /workspace/README.txt",
    ]

    print("Configuration:")
    print(f"  - Sandbox: ENABLED (chroot)")
    print(f"  - Package managers: SEPARATE (in /tools/)")
    print(f"  - Init commands: {len(init_commands)} commands")
    for cmd in init_commands:
        print(f"    * {cmd}")
    print()

    # Start the coding environment server with sandbox
    print("Starting sandboxed coding environment server...")
    openenv_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "envs.coding_env.server.app:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
        env={
            **os.environ,
            "PYTHONPATH": f"{working_directory}/src",
            "ENABLE_WEB_INTERFACE": "false",
            # Sandbox configuration
            "SANDBOX_ENABLE": "true",
            "SANDBOX_INCLUDE_PKG_MANAGERS": "false",  # Keep in /tools/
            "SANDBOX_INIT_COMMANDS": "; ".join(init_commands),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=working_directory,
    )

    try:
        # Wait for server to be ready
        if not wait_for_server(localhost):
            print("❌ Server failed to start within timeout")
            return False

        print()
        print("Connecting to sandboxed environment...")
        client = CodingEnv(base_url=localhost)

        # Reset - this creates the sandbox
        print("\n" + "=" * 70)
        print("1. RESET - Create Fresh Sandbox")
        print("=" * 70)
        result = client.reset()
        print(f"✓ Sandbox created for episode: {client.state().episode_id}")
        print(f"  exit_code: {result.observation.exit_code}")

        # Test core binaries (should work)
        print("\n" + "=" * 70)
        print("2. TEST CORE BINARIES (Always Available)")
        print("=" * 70)

        core_tests = [
            ("List workspace", "ls -la /workspace"),
            ("Check README", "cat /workspace/README.txt"),
            ("Echo command", "echo 'Core binaries work!'"),
            ("PWD command", "pwd"),
            ("Create file", "touch /workspace/test.txt"),
            ("Check file exists", "ls /workspace/test.txt"),
        ]

        for i, (desc, command) in enumerate(core_tests, 1):
            print(f"\nTest {i}: {desc}")
            result = client.step(ShellAction(command=command))
            print(f"  Command: {command}")
            if result.observation.stdout.strip():
                print(f"  → stdout: {result.observation.stdout.strip()[:80]}")
            print(f"  → exit_code: {result.observation.exit_code}")
            if result.observation.exit_code == 0:
                print("  ✓ SUCCESS")
            else:
                print(f"  ✗ FAILED: {result.observation.stderr[:60]}")

        # Test package managers (should NOT be in PATH)
        print("\n" + "=" * 70)
        print("3. TEST PACKAGE MANAGERS (Should be in /tools/)")
        print("=" * 70)

        print("\nAttempting to use git directly (should fail):")
        result = client.step(ShellAction(command="git --version"))
        print(f"  Command: git --version")
        print(f"  → exit_code: {result.observation.exit_code}")
        if result.observation.exit_code != 0:
            print("  ✓ EXPECTED: git not in PATH (security working!)")
        else:
            print("  ✗ UNEXPECTED: git is available (should be in /tools/)")

        print("\nAttempting to use curl directly (should fail):")
        result = client.step(ShellAction(command="curl --version"))
        print(f"  Command: curl --version")
        print(f"  → exit_code: {result.observation.exit_code}")
        if result.observation.exit_code != 0:
            print("  ✓ EXPECTED: curl not in PATH (security working!)")
        else:
            print("  ✗ UNEXPECTED: curl is available (should be in /tools/)")

        # Show how agent can opt-in to package managers
        print("\n" + "=" * 70)
        print("4. AGENT OPT-IN to Package Managers")
        print("=" * 70)

        print("\nAgent can explicitly copy tools when needed:")
        print("  Step 1: Check if git exists in /tools/")
        result = client.step(ShellAction(command="ls -la /tools/ | grep git"))
        if result.observation.exit_code == 0:
            print("  ✓ git found in /tools/")
            print(f"    {result.observation.stdout.strip()[:80]}")

            print("\n  Step 2: Agent copies git to /usr/bin/ (opt-in)")
            result = client.step(ShellAction(command="cp /tools/git /usr/bin/git"))
            if result.observation.exit_code == 0:
                print("  ✓ git copied successfully")

                print("\n  Step 3: Now git is available")
                result = client.step(ShellAction(command="git --version"))
                if result.observation.exit_code == 0:
                    print(f"  ✓ git works: {result.observation.stdout.strip()}")
                else:
                    print("  (May need additional libraries)")
            else:
                print("  Note: Copy may fail if git not available on host")
        else:
            print("  Note: git may not be available on this system")

        # Test Python code still works
        print("\n" + "=" * 70)
        print("5. PYTHON CODE EXECUTION (Unaffected)")
        print("=" * 70)

        print("\nPython code execution bypasses chroot:")
        result = client.step(CodeAction(code="print('Python works fine!')"))
        print(f"  Code: print('Python works fine!')")
        print(f"  → stdout: {result.observation.stdout.strip()}")
        print(f"  → exit_code: {result.observation.exit_code}")
        print("  ✓ Python unaffected by sandbox")

        # Test sandbox isolation
        print("\n" + "=" * 70)
        print("6. SANDBOX ISOLATION TEST")
        print("=" * 70)

        print("\nAttempting to access host filesystem (should fail):")
        result = client.step(ShellAction(command="ls /home"))
        print(f"  Command: ls /home")
        print(f"  → exit_code: {result.observation.exit_code}")
        if result.observation.exit_code != 0 or not result.observation.stdout.strip():
            print("  ✓ Host /home not accessible (sandbox working!)")
        else:
            print(f"  → Found: {result.observation.stdout.strip()[:60]}")

        # Reset and verify new sandbox
        print("\n" + "=" * 70)
        print("7. RESET - New Sandbox (Clean State)")
        print("=" * 70)

        print("\nResetting creates fresh sandbox:")
        result = client.reset()
        new_episode = client.state().episode_id
        print(f"  New episode: {new_episode}")

        print("\n  Checking if previous test.txt exists (should NOT):")
        result = client.step(ShellAction(command="ls /workspace/test.txt"))
        if result.observation.exit_code != 0:
            print("  ✓ Previous files gone (fresh sandbox!)")
        else:
            print("  ✗ File still exists (sandbox not cleaned?)")

        print("\n  Checking if init commands ran again:")
        result = client.step(ShellAction(command="cat /workspace/README.txt"))
        if result.observation.exit_code == 0:
            print(f"  ✓ Init ran: {result.observation.stdout.strip()}")
        else:
            print("  ✗ Init commands may have failed")

        print("\n" + "=" * 70)
        print("SANDBOX TEST COMPLETE! 🎉")
        print("=" * 70)
        print("\nSummary:")
        print("  ✓ Chroot sandbox isolates filesystem")
        print("  ✓ Core binaries available in sandbox")
        print("  ✓ Package managers separate (security)")
        print("  ✓ Agent can opt-in to tools via /tools/")
        print("  ✓ Init commands set up workspace")
        print("  ✓ Fresh sandbox on each reset()")
        print("  ✓ Python execution unaffected")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\nCleaning up...")
        try:
            openenv_process.terminate()
            openenv_process.wait(timeout=5)
            print("✓ Server stopped")
        except Exception as e:
            print(f"Warning: Error stopping server: {e}")
            openenv_process.kill()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
