# Coding Environment

A Python code execution environment that runs arbitrary Python code and shell commands, returning results. Perfect for testing code execution infrastructure and demonstrating environment usage patterns.

## Quick Start

The simplest way to use the Coding environment is through the `CodingEnv` class:

```python
from envs.coding_env import CodeAction, ShellAction, CodingEnv

try:
    # Create environment from Docker image
    coding_env = CodingEnv.from_docker_image("coding-env:latest")

    # Reset
    result = coding_env.reset()
    print(f"Reset complete: exit_code={result.observation.exit_code}")

    # Execute Python code
    code_samples = [
        "print('Hello, World!')",
        "x = 5 + 3\nprint(f'Result: {x}')",
        "import math\nprint(math.pi)"
    ]

    for code in code_samples:
        result = coding_env.step(CodeAction(code=code))
        print(f"Code: {code}")
        print(f"  → stdout: {result.observation.stdout.strip()}")
        print(f"  → exit_code: {result.observation.exit_code}")

    # Execute shell commands
    result = coding_env.step(ShellAction(command="echo 'Hello from shell!'"))
    print(f"Shell: {result.observation.stdout.strip()}")

    # Mix Python and shell
    result = coding_env.step(ShellAction(command="ls -la"))
    print(f"Directory listing: {result.observation.stdout}")

finally:
    # Always clean up
    coding_env.close()
```

That's it! The `CodingEnv.from_docker_image()` method handles:
- Starting the Docker container
- Waiting for the server to be ready
- Connecting to the environment
- Container cleanup when you call `close()`

## Building the Docker Image

Before using the environment, you need to build the Docker image:

```bash
# From project root
docker build -t coding-env:latest -f src/envs/coding_env/server/Dockerfile .
```

## Environment Details

### Actions
**CodeAction**: Execute Python code
- `code` (str) - The Python code to execute

**ShellAction**: Execute shell commands
- `command` (str) - The shell command to execute
- `timeout` (int) - Maximum seconds to wait for command completion (default: 30)

### Observation
**CodeObservation**: Contains the execution results
- `stdout` (str) - Standard output from code execution
- `stderr` (str) - Standard error from code execution
- `exit_code` (int) - Exit code (0 for success, non-zero for errors)

### State
**CodeState**: Tracks execution state
- `episode_id` (str) - Unique identifier for the episode
- `step_count` (int) - Number of steps taken
- `last_exit_code` (int) - Exit code from the last execution

## Advanced Usage

### Connecting to an Existing Server

If you already have a Coding environment server running, you can connect directly:

```python
from envs.coding_env import CodingEnv, CodeAction, ShellAction

# Connect to existing server
coding_env = CodingEnv(base_url="<ENV_HTTP_URL_HERE>")

# Use as normal
result = coding_env.reset()
result = coding_env.step(CodeAction(code="print('Hello!')"))

# Execute shell commands
result = coding_env.step(ShellAction(command="pwd"))
```

Note: When connecting to an existing server, `coding_env.close()` will NOT stop the server.

## Development & Testing

### Running the Examples

**Basic Python code execution:**
```bash
python3 examples/local_coding_env.py
```

**Python code + shell commands:**
```bash
python3 examples/local_coding_env_with_shell.py
```

**Test ShellExecutor directly (no Docker needed):**
```bash
python3 examples/test_shell_executor.py
```

These examples show:
- Creating an environment from a Docker image
- Resetting and executing code through the environment
- Executing shell commands with timeout control
- Mixing Python code and shell commands in the same session
- Automatic cleanup with `close()`

## Shell Command Examples

### Basic Shell Commands

```python
from envs.coding_env import ShellAction, CodingEnv

client = CodingEnv.from_docker_image("coding-env:latest")

# List files
result = client.step(ShellAction(command="ls -la"))
print(result.observation.stdout)

# Check current directory
result = client.step(ShellAction(command="pwd"))
print(result.observation.stdout)

# Create and read a file
client.step(ShellAction(command="echo 'test' > /tmp/file.txt"))
result = client.step(ShellAction(command="cat /tmp/file.txt"))
print(result.observation.stdout)  # "test"

client.close()
```

### Shell Commands with Timeout

```python
from envs.coding_env import ShellAction, CodingEnv

client = CodingEnv.from_docker_image("coding-env:latest")

# Quick command (completes within timeout)
result = client.step(ShellAction(command="echo 'done'", timeout=5))
print(result.observation.exit_code)  # 0

# Long-running command (will timeout)
result = client.step(ShellAction(command="sleep 100", timeout=2))
print(result.observation.exit_code)  # 124 (timeout exit code)
print(result.observation.stderr)  # "Command timed out after 2 seconds"

client.close()
```

### Mixing Python and Shell

```python
from envs.coding_env import CodeAction, ShellAction, CodingEnv

client = CodingEnv.from_docker_image("coding-env:latest")
client.reset()

# Python: Define a variable
client.step(CodeAction(code="data = [1, 2, 3, 4, 5]"))

# Shell: Create output directory
client.step(ShellAction(command="mkdir -p /tmp/output"))

# Python: Process data
result = client.step(CodeAction(code="print(sum(data))"))
print(result.observation.stdout)  # "15"

# Shell: Save results
client.step(ShellAction(command="echo 'Results saved' > /tmp/output/results.txt"))

# Shell: Verify
result = client.step(ShellAction(command="cat /tmp/output/results.txt"))
print(result.observation.stdout)  # "Results saved"

client.close()
```

## Project Structure

```
coding_env/
├── README.md              # This file
├── models.py              # Action, Observation, and State models
├── client/
│   ├── coding_env_client.py  # CodingEnv client implementation
│   └── example_usage.py      # Usage examples
└── server/
    ├── python_codeact_env.py  # Core environment logic
    ├── app.py                 # FastAPI application
    ├── transforms.py          # Observation transforms
    ├── Dockerfile             # Container image definition
    └── README.md              # Server-specific documentation
```
