# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

#!/usr/bin/env python3
"""
Standalone test for ShellExecutor.

This script tests the ShellExecutor tool directly without needing Docker
or the full environment setup.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.tools import ShellExecutor


def test_basic_commands():
    """Test basic shell command execution."""
    print("\n" + "=" * 60)
    print("Test 1: Basic Shell Commands")
    print("=" * 60)

    executor = ShellExecutor()

    # Test echo command (works on both Windows and Unix)
    print("\n1. Echo command:")
    result = executor.run("echo Hello, World!")
    print(f"   stdout: {result.stdout.strip()}")
    print(f"   stderr: {result.stderr.strip()}")
    print(f"   exit_code: {result.exit_code}")
    assert result.exit_code == 0, "Echo command should succeed"
    assert "Hello, World!" in result.stdout, "Output should contain echoed text"
    print("   ✓ PASSED")

    # Test multiline command
    print("\n2. Multi-line output:")
    result = executor.run("echo Line1 && echo Line2 && echo Line3")
    print(f"   stdout: {result.stdout.strip()}")
    print(f"   exit_code: {result.exit_code}")
    assert result.exit_code == 0, "Multi-line command should succeed"
    print("   ✓ PASSED")


def test_error_handling():
    """Test error handling for failed commands."""
    print("\n" + "=" * 60)
    print("Test 2: Error Handling")
    print("=" * 60)

    executor = ShellExecutor()

    # Test nonexistent command
    print("\n1. Nonexistent command:")
    result = executor.run("nonexistent_command_12345")
    print(f"   exit_code: {result.exit_code}")
    print(f"   stderr: {result.stderr[:100]}...")
    assert result.exit_code != 0, "Nonexistent command should fail"
    print("   ✓ PASSED")

    # Test command with error
    print("\n2. Command with error (invalid syntax):")
    result = executor.run("cd /nonexistent/path/xyz123")
    print(f"   exit_code: {result.exit_code}")
    if result.stderr:
        print(f"   stderr: {result.stderr[:100]}...")
    assert result.exit_code != 0, "Invalid path should fail"
    print("   ✓ PASSED")


def test_timeout():
    """Test timeout functionality."""
    print("\n" + "=" * 60)
    print("Test 3: Timeout Handling")
    print("=" * 60)

    # Test command that completes within timeout
    print("\n1. Command completes within timeout:")
    executor = ShellExecutor(timeout=5)

    # Use ping with count (works on both Windows and Unix)
    # Windows: ping -n 1, Unix: ping -c 1
    import platform

    if platform.system() == "Windows":
        result = executor.run("ping -n 1 127.0.0.1")
    else:
        result = executor.run("ping -c 1 127.0.0.1")

    print(f"   exit_code: {result.exit_code}")
    print(f"   stdout length: {len(result.stdout)} chars")
    assert result.exit_code == 0, "Quick ping should complete"
    print("   ✓ PASSED")

    # Test command that times out
    print("\n2. Command exceeds timeout:")
    executor = ShellExecutor(timeout=2)

    # Use a sleep-like command that works on both platforms
    if platform.system() == "Windows":
        # PowerShell sleep command
        result = executor.run("powershell -Command Start-Sleep -Seconds 10")
    else:
        result = executor.run("sleep 10")

    print(f"   exit_code: {result.exit_code}")
    print(f"   stderr: {result.stderr[:100]}...")
    assert result.exit_code == 124, "Timeout should return exit code 124"
    assert "timed out" in result.stderr.lower(), "Stderr should mention timeout"
    print("   ✓ PASSED")


def test_output_capture():
    """Test capturing stdout and stderr separately."""
    print("\n" + "=" * 60)
    print("Test 4: Output Capture")
    print("=" * 60)

    executor = ShellExecutor()

    # Test stdout capture
    print("\n1. Stdout capture:")
    result = executor.run("echo This goes to stdout")
    print(f"   stdout: {result.stdout.strip()}")
    print(f"   stderr: '{result.stderr.strip()}'")
    assert len(result.stdout) > 0, "Should capture stdout"
    assert "stdout" in result.stdout.lower(), "Should contain expected text"
    print("   ✓ PASSED")


def test_working_directory():
    """Test working directory parameter."""
    print("\n" + "=" * 60)
    print("Test 5: Working Directory")
    print("=" * 60)

    import tempfile
    import os

    # Create a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n1. Execute command in temp directory: {tmpdir}")

        executor = ShellExecutor(cwd=tmpdir)

        # Get current directory
        import platform

        if platform.system() == "Windows":
            result = executor.run("cd")
        else:
            result = executor.run("pwd")

        print(f"   Current directory: {result.stdout.strip()}")
        # Normalize paths for comparison
        result_path = os.path.normpath(result.stdout.strip())
        expected_path = os.path.normpath(tmpdir)
        assert result_path == expected_path or result_path.startswith(expected_path), (
            f"Should be in temp directory. Expected: {expected_path}, Got: {result_path}"
        )
        print("   ✓ PASSED")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ShellExecutor Test Suite")
    print("=" * 60)

    try:
        test_basic_commands()
        test_error_handling()
        test_timeout()
        test_output_capture()
        test_working_directory()

        print("\n" + "=" * 60)
        print("All tests PASSED! 🎉")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
