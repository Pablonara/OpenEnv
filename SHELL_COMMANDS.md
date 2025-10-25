# Shell Command Execution in OpenEnv

This guide documents the shell command execution feature added to the Coding Environment, allowing agents to execute both Python code and shell commands within the same environment.

## Overview

The **ShellExecutor** tool enables safe execution of shell commands in isolated environments, perfect for RL agents that need to interact with the file system, run system utilities, or perform operations beyond Python code execution.

### Features

- ✅ **Safe subprocess execution** - Commands run in isolated subprocesses
- ✅ **Configurable timeouts** - Prevent hanging commands
- ✅ **Full output capture** - Captures stdout, stderr, and exit codes
- ✅ **Cross-platform** - Works on Windows, Linux, and macOS
- ✅ **Custom working directory** - Execute commands in specific directories
- ✅ **Seamless integration** - Works alongside Python code execution in CodingEnv

## Quick Start

### Standalone Usage (ShellExecutor)

```python
from core.tools import ShellExecutor

# Create executor
executor = ShellExecutor(timeout=30)

# Run a command
result = executor.run("ls -la")

print(result.stdout)      # Command output
print(result.stderr)      # Error messages
print(result.exit_code)   # 0 for success, non-zero for errors
```

### Integrated Usage (CodingEnv)

```python
from envs.coding_env import CodingEnv, CodeAction, ShellAction

# Create environment
env = CodingEnv.from_docker_image("coding-env:latest")

# Reset
env.reset()

# Execute Python code
result = env.step(CodeAction(code="x = 42\nprint(x)"))
print(result.observation.stdout)  # "42"

# Execute shell command
result = env.step(ShellAction(command="echo 'Hello Shell!'"))
print(result.observation.stdout)  # "Hello Shell!"

# Cleanup
env.close()
```

## API Reference

### ShellExecutor Class

```python
class ShellExecutor:
    def __init__(
        self,
        timeout: int = 30,
        shell: bool = True,
        cwd: Optional[str] = None,
    )
```

**Parameters:**
- `timeout` (int): Maximum seconds to wait for command completion. Default: 30
- `shell` (bool): Whether to execute through shell. Default: True
- `cwd` (str, optional): Working directory for command execution. Default: None (current directory)

**Methods:**
- `run(command: str) -> CodeExecResult`: Execute a shell command and return results

### ShellAction Class

```python
@dataclass
class ShellAction(Action):
    command: str      # Shell command to execute
    timeout: int = 30 # Maximum seconds to wait
```

**Fields:**
- `command` (str): The shell command string to execute
- `timeout` (int): Maximum time in seconds. Default: 30

### CodeExecResult

```python
@dataclass
class CodeExecResult:
    stdout: str      # Standard output from command
    stderr: str      # Standard error from command
    exit_code: int   # Exit code (0 = success, non-zero = error)
```

## Usage Examples

### Example 1: File Operations

```python
from envs.coding_env import CodingEnv, ShellAction

env = CodingEnv.from_docker_image("coding-env:latest")
env.reset()

# Create directory
env.step(ShellAction(command="mkdir -p /tmp/mydata"))

# Create file
env.step(ShellAction(command="echo 'sample data' > /tmp/mydata/file.txt"))

# Read file
result = env.step(ShellAction(command="cat /tmp/mydata/file.txt"))
print(result.observation.stdout)  # "sample data"

# List files
result = env.step(ShellAction(command="ls -l /tmp/mydata"))
print(result.observation.stdout)

env.close()
```

### Example 2: System Information

```python
from core.tools import ShellExecutor

executor = ShellExecutor()

# Get current directory
result = executor.run("pwd")
print(f"Current directory: {result.stdout.strip()}")

# Get system info
result = executor.run("uname -a")
print(f"System: {result.stdout.strip()}")

# Check disk space
result = executor.run("df -h")
print(f"Disk space:\n{result.stdout}")

# Get date/time
result = executor.run("date")
print(f"Current time: {result.stdout.strip()}")
```

### Example 3: Mixing Python and Shell

```python
from envs.coding_env import CodingEnv, CodeAction, ShellAction

env = CodingEnv.from_docker_image("coding-env:latest")
env.reset()

# Python: Generate data
env.step(CodeAction(code="""
data = [10, 20, 30, 40, 50]
total = sum(data)
print(f'Total: {total}')
"""))

# Shell: Create output directory
env.step(ShellAction(command="mkdir -p /tmp/results"))

# Python: Save results to variable
env.step(CodeAction(code="""
result_text = f'Sum of data: {total}'
print(result_text)
"""))

# Shell: Save to file
env.step(ShellAction(command="echo 'Processing complete' > /tmp/results/status.txt"))

# Shell: Verify
result = env.step(ShellAction(command="cat /tmp/results/status.txt"))
print(result.observation.stdout)

env.close()
```

### Example 4: Timeout Handling

```python
from core.tools import ShellExecutor

# Create executor with 5 second timeout
executor = ShellExecutor(timeout=5)

# This will complete successfully
result = executor.run("echo 'Quick command'")
print(f"Exit code: {result.exit_code}")  # 0

# This will timeout after 5 seconds
result = executor.run("sleep 10")
print(f"Exit code: {result.exit_code}")  # 124 (timeout)
print(f"Error: {result.stderr}")  # "Command timed out after 5 seconds"
```

### Example 5: Error Handling

```python
from core.tools import ShellExecutor

executor = ShellExecutor()

# Successful command
result = executor.run("echo 'Success'")
if result.exit_code == 0:
    print(f"Success: {result.stdout}")
else:
    print(f"Failed: {result.stderr}")

# Failed command
result = executor.run("nonexistent_command")
if result.exit_code != 0:
    print(f"Command failed with exit code {result.exit_code}")
    print(f"Error message: {result.stderr}")

# Permission denied
result = executor.run("cat /etc/shadow")
if result.exit_code != 0:
    print("Permission denied or file not accessible")
```

### Example 6: Working Directory

```python
from core.tools import ShellExecutor
import tempfile

# Create temp directory
tmpdir = tempfile.mkdtemp()

# Execute commands in specific directory
executor = ShellExecutor(cwd=tmpdir)

# Create file in that directory
result = executor.run("echo 'test' > data.txt")

# Read it back
result = executor.run("cat data.txt")
print(result.stdout)  # "test"

# Verify location
result = executor.run("pwd")
print(f"Working in: {result.stdout.strip()}")
```

## Testing

### Run Standalone Tests

Test the ShellExecutor without Docker:

```bash
python examples/test_shell_executor_simple.py
```

### Run Full Integration Tests

Test with the complete CodingEnv (requires Docker):

```bash
# Build the Docker image first
docker build -t coding-env:latest -f src/envs/coding_env/server/Dockerfile .

# Run the test
python examples/local_coding_env_with_shell.py
```

## Platform-Specific Considerations

### Windows

- Use PowerShell commands for advanced operations:
  ```python
  result = executor.run("powershell -Command Get-ChildItem")
  ```
- Path separators use backslash (`\`) or forward slash (`/`)
- Some Unix commands have Windows equivalents:
  - `ls` → `dir`
  - `cat` → `type`
  - `rm` → `del`

### Linux/macOS

- Standard Unix commands work out of the box
- Use bash-specific features when needed:
  ```python
  result = executor.run("bash -c 'source ~/.bashrc && env'")
  ```

## Safety Considerations

### Sandboxing

When using ShellExecutor in the CodingEnv Docker container:
- Commands execute in an isolated container
- Limited access to host system
- No direct access to host file system (unless volumes mounted)

### Timeout Protection

Always set reasonable timeouts to prevent:
- Hanging processes
- Resource exhaustion
- Denial of service

```python
# Good: Set appropriate timeout
executor = ShellExecutor(timeout=30)

# Dangerous: No timeout limit (not recommended)
executor = ShellExecutor(timeout=999999)
```

### Input Validation

For production RL systems, validate commands before execution:

```python
def is_safe_command(command: str) -> bool:
    """Check if command is safe to execute."""
    dangerous_patterns = [
        'rm -rf /',
        'mkfs',
        'dd if=/dev/',
        ':(){ :|:& };:',  # Fork bomb
    ]
    
    return not any(pattern in command for pattern in dangerous_patterns)

# Use validation
if is_safe_command(user_command):
    result = executor.run(user_command)
else:
    print("Command blocked for safety reasons")
```

## Integration with RL Training

### Reward Shaping

Use exit codes and output for reward signals:

```python
# Execute command
result = env.step(ShellAction(command="test -f /tmp/expected_file.txt"))

# Reward based on success
if result.observation.exit_code == 0:
    reward = 1.0  # File exists
else:
    reward = -0.5  # File doesn't exist
```

### Multi-Step Tasks

Chain Python and shell operations:

```python
# Step 1: Generate script with Python
env.step(CodeAction(code="""
script = '''#!/bin/bash
echo "Generated script"
'''
print(script)
"""))

# Step 2: Save script with shell
env.step(ShellAction(command="echo '#!/bin/bash\\necho Generated' > /tmp/script.sh"))

# Step 3: Make executable
env.step(ShellAction(command="chmod +x /tmp/script.sh"))

# Step 4: Execute
result = env.step(ShellAction(command="/tmp/script.sh"))
```

## Troubleshooting

### Command Not Found

**Problem:** `exit_code != 0`, stderr contains "command not found"

**Solution:** Ensure the command is available in the container/environment:
```bash
# Check if command exists
result = executor.run("which ls")
```

### Timeout Issues

**Problem:** Commands timing out unexpectedly

**Solution:** Increase timeout or optimize command:
```python
# Increase timeout
executor = ShellExecutor(timeout=60)

# Or optimize the command
# Bad: result = executor.run("find / -name file.txt")
# Good: result = executor.run("find /home -name file.txt")
```

### Permission Denied

**Problem:** `exit_code != 0`, stderr contains "permission denied"

**Solution:** Run container with appropriate permissions or adjust file permissions:
```python
# Adjust permissions
env.step(ShellAction(command="chmod 644 /tmp/file.txt"))
```

## Future Enhancements

Potential improvements for future versions:

- [ ] Command history and replay
- [ ] Interactive shell sessions (persistent shell state)
- [ ] Command whitelisting/blacklisting
- [ ] Resource usage monitoring (CPU, memory)
- [ ] Async command execution
- [ ] Command chaining with pipes
- [ ] Environment variable management

## Contributing

To extend or improve shell command functionality:

1. Modify `src/core/tools/shell_executor.py`
2. Add tests to `examples/test_shell_executor_simple.py`
3. Update documentation in this file
4. Submit PR with examples

## Related Documentation

- [Coding Environment README](src/envs/coding_env/README.md)
- [Core Tools](src/core/tools/)
- [Environment Server](src/core/env_server/)

## License

BSD 3-Clause License - See LICENSE file