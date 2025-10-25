#!/usr/bin/env python3
"""
Minimal standalone test for ShellExecutor.
Tests the shell executor directly without environment dependencies.
"""

import subprocess
import platform
from dataclasses import dataclass


@dataclass
class CodeExecResult:
    """Result of code execution containing stdout, stderr, and exit code."""

    stdout: str
    stderr: str
    exit_code: int


class ShellExecutor:
    """Minimal ShellExecutor for testing."""

    def __init__(self, timeout: int = 30, shell: bool = True, cwd: str = None):
        self.timeout = timeout
        self.shell = shell
        self.cwd = cwd

    def run(self, command: str) -> CodeExecResult:
        """Execute a shell command and return the result."""
        try:
            process = subprocess.Popen(
                command,
                shell=self.shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.cwd,
            )

            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                exit_code = process.returncode

                return CodeExecResult(
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                )

            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()

                return CodeExecResult(
                    stdout=stdout,
                    stderr=f"Command timed out after {self.timeout} seconds\n{stderr}",
                    exit_code=124,
                )

        except Exception as e:
            return CodeExecResult(
                stdout="",
                stderr=f"Shell execution error: {str(e)}",
                exit_code=1,
            )


def test_basic_commands():
    """Test basic shell command execution."""
    print("\n" + "=" * 60)
    print("Test 1: Basic Shell Commands")
    print("=" * 60)

    executor = ShellExecutor()

    # Test echo command
    print("\n1. Echo command:")
    result = executor.run("echo Hello World")
    print(f"   stdout: {result.stdout.strip()}")
    print(f"   exit_code: {result.exit_code}")
    assert result.exit_code == 0, "Echo command should succeed"
    assert "Hello" in result.stdout, "Output should contain text"
    print("   ✓ PASSED")


def test_error_handling():
    """Test error handling for failed commands."""
    print("\n" + "=" * 60)
    print("Test 2: Error Handling")
    print("=" * 60)

    executor = ShellExecutor()

    # Test nonexistent command
    print("\n1. Nonexistent command:")
    result = executor.run("nonexistent_cmd_xyz123")
    print(f"   exit_code: {result.exit_code}")
    assert result.exit_code != 0, "Nonexistent command should fail"
    print("   ✓ PASSED")


def test_timeout():
    """Test timeout functionality."""
    print("\n" + "=" * 60)
    print("Test 3: Timeout Handling")
    print("=" * 60)

    # Test command that times out
    print("\n1. Command exceeds timeout:")
    executor = ShellExecutor(timeout=2)

    # Use platform-appropriate sleep command
    if platform.system() == "Windows":
        result = executor.run("powershell -Command Start-Sleep -Seconds 5")
    else:
        result = executor.run("sleep 5")

    print(f"   exit_code: {result.exit_code}")
    print(f"   stderr preview: {result.stderr[:60]}...")
    assert result.exit_code == 124, "Timeout should return exit code 124"
    assert "timed out" in result.stderr.lower(), "Stderr should mention timeout"
    print("   ✓ PASSED")


def test_output_capture():
    """Test capturing stdout."""
    print("\n" + "=" * 60)
    print("Test 4: Output Capture")
    print("=" * 60)

    executor = ShellExecutor()

    # Test stdout capture
    print("\n1. Stdout capture:")
    result = executor.run("echo Testing output capture")
    print(f"   stdout: {result.stdout.strip()}")
    assert len(result.stdout) > 0, "Should capture stdout"
    assert "Testing" in result.stdout, "Should contain expected text"
    print("   ✓ PASSED")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ShellExecutor Simple Test Suite")
    print("=" * 60)

    try:
        test_basic_commands()
        test_error_handling()
        test_timeout()
        test_output_capture()

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
    import sys

    success = main()
    sys.exit(0 if success else 1)
