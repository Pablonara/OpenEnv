# Chroot Environment

A sandboxed code/command execution environment that uses chroot to isolate execution contexts. This environment copies a target directory into a temporary location and symlinks system binaries, allowing safe execution of commands within a restricted filesystem hierarchy.

## Quick Start

The simplest way to use the Chroot environment is through the `ChrootEnv` class:

```python
from envs.chroot_env import ChrootAction, ChrootEnv

try:
    # Create environment from Docker image
    chroot_env = ChrootEnv.from_docker_image(
        "chroot-env:latest",
        env_vars={
            "TARGET_DIR": "/path/to/project",
            "SYMLINK_DIRS": "/bin,/usr/bin,/usr/local/bin"
        }
    )

    # Reset
    result = chroot_env.reset()
    print(f"Reset complete: exit_code={result.observation.exit_code}")

    # Execute commands in the chroot sandbox
    commands = [
        "pwd",
        "ls -la",
        "echo 'Hello from chroot'",
        "cat /etc/passwd",  # Will fail - no passwd in chroot
    ]

    for cmd in commands:
        result = chroot_env.step(ChrootAction(command=cmd))
        print(f"Command: {cmd}")
        print(f"  → stdout: {result.observation.stdout.strip()}")
        print(f"  → exit_code: {result.observation.exit_code}")

finally:
    # Always clean up
    chroot_env.close()
```

That's it! The `ChrootEnv.from_docker_image()` method handles:
- Starting the Docker container
- Waiting for the server to be ready
- Connecting to the environment
- Container cleanup when you call `close()`

## Building the Docker Image

Before using the environment, you need to build the Docker image:

```bash
# From project root
docker build -t chroot-env:latest -f src/envs/chroot_env/server/Dockerfile .
```

## Environment Details

### Action
**ChrootAction**: Contains a single field
- `command` (str) - The shell command to execute in the chroot sandbox

### Observation
**ChrootObservation**: Contains the execution results
- `stdout` (str) - Standard output from command execution
- `stderr` (str) - Standard error from command execution
- `exit_code` (int) - Exit code (0 for success, non-zero for errors)

### State
**ChrootState**: Tracks execution state
- `episode_id` (str) - Unique identifier for the episode
- `step_count` (int) - Number of steps taken
- `last_exit_code` (int) - Exit code from the last execution

## Configuration

The chroot environment can be configured via environment variables when running the server:

- **TARGET_DIR**: Directory to copy into the chroot sandbox (default: `/tmp/default_target`)
- **SYMLINK_DIRS**: Comma-separated list of system directories to symlink into the chroot (default: `/bin,/usr/bin,/usr/local/bin`)
- **SHELL**: Shell to use for command execution (default: `/bin/bash`)

Example Docker run with custom target directory:

```bash
docker run -e TARGET_DIR=/my/project -p 8000:8000 chroot-env:latest
```

## How It Works

1. **Directory Copy**: When `reset()` is called, the TARGET_DIR is copied to a temporary directory
2. **Symlink Setup**: System binaries from specified directories (SYMLINK_DIRS) are symlinked into the chroot
3. **Command Execution**: Commands are executed within the chroot sandbox using the specified shell
4. **Cleanup**: When the episode ends or the environment is destroyed, the temporary directory is cleaned up

## Advanced Usage

### Connecting to an Existing Server

If you already have a Chroot environment server running, you can connect directly:

```python
from envs.chroot_env import ChrootEnv

# Connect to existing server
chroot_env = ChrootEnv(base_url="<ENV_HTTP_URL_HERE>")

# Use as normal
result = chroot_env.reset()
result = chroot_env.step(ChrootAction(command="ls -la"))
```

Note: When connecting to an existing server, `chroot_env.close()` will NOT stop the server.

## Security Considerations

- The chroot environment provides filesystem isolation but is **not a complete security sandbox**
- Commands still run with the same privileges as the container process
- Dangerous operations are detected and penalized via the ChrootSafetyTransform
- For maximum security, run the container with reduced privileges (e.g., `--cap-drop ALL`)

## Project Structure

```
chroot_env/
├── README.md                  # This file
├── models.py                  # Action, Observation, and State models
├── chroot_env_client.py       # ChrootEnv client implementation
└── server/
    ├── python_chroot_env.py   # Core environment logic with chroot setup
    ├── app.py                 # FastAPI application
    ├── transforms.py          # Observation transforms for safety/execution
    ├── Dockerfile             # Container image definition
    └── README.md              # Server-specific documentation
```

## Limitations

- Chroot is not a complete container - it requires proper setup of system libraries and binaries
- The environment runs as a Linux-specific feature and requires `--privileged` or `--cap-add SYS_ADMIN` for Docker
- Command execution timeout is fixed at 30 seconds
- The sandbox is cleaned up after each episode
