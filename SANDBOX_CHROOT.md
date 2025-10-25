# Chroot Sandbox for Coding Environment

This document describes the chroot sandbox feature for secure shell command execution in the OpenEnv Coding Environment, designed specifically for RL training scenarios.

## Overview

The chroot sandbox provides **filesystem isolation** for shell commands executed by RL agents, while maintaining full flexibility for exploration and learning. This allows agents to:

- ✅ Execute any shell commands freely (for RL exploration)
- ✅ Have isolated filesystem (can't damage host system)
- ✅ Start with clean workspace each episode (via `reset()`)
- ✅ Opt-in to package managers (security by default)
- ✅ Initialize workspace with custom setup (init hooks)

## Why Chroot for RL?

Traditional sandboxing approaches (whitelists, blacklists) are **incompatible with RL** because:
- Agents need to explore and discover actions
- Restricting commands prevents learning
- Unknown valid solutions may be blocked

**Chroot provides the best of both worlds:**
- Agent has full command flexibility
- Host system remains protected
- Each episode gets fresh, isolated environment

## Architecture

```
Host System
│
├── /tmp/sandbox_<episode_id>/          ← Chroot Jail (isolated)
│   ├── bin/                            ← Core utilities (ls, cat, bash, etc.)
│   ├── usr/bin/                        ← Empty initially
│   ├── lib/ & lib64/                   ← Required shared libraries
│   ├── tmp/                            ← Writable temp space
│   ├── workspace/                      ← Agent's working directory
│   │   └── README.txt                  ← Created by init_commands
│   └── tools/                          ← Package managers (git, curl, apt)
│                                         Agent must explicitly copy to use
│
└── Python Code Executor                ← Runs outside chroot (no isolation)
```

### Key Design Principles

1. **Core Binaries Always Available**: Essential commands (bash, ls, cat, mkdir, etc.) are in `/bin/`
2. **Package Managers Separate**: Network tools (curl, git, apt) are in `/tools/` - agent must opt-in
3. **Init Hooks**: Custom commands run during sandbox creation (e.g., git clone, mkdir)
4. **Episode Isolation**: Fresh chroot created on each `reset()`
5. **Python Unaffected**: Python code execution bypasses chroot for full functionality

## Configuration

### SandboxConfig Class

```python
from envs.coding_env import SandboxConfig

config = SandboxConfig(
    enable=True,                          # Enable chroot sandbox
    init_commands=[                       # Commands to run during setup
        "mkdir -p /workspace/project",
        "echo 'Setup complete' > /workspace/status.txt"
    ],
    include_package_managers=False        # If False, pkg managers in /tools/
)
```

**Fields:**
- `enable` (bool): Enable/disable chroot sandboxing (default: `True`)
- `init_commands` (List[str]): Shell commands executed during sandbox creation
- `include_package_managers` (bool): If `True`, package managers available in PATH. If `False`, they're in `/tools/` (default: `False`)

### Environment Variables

When launching the server, configure via environment variables:

```python
env = {
    "SANDBOX_ENABLE": "true",                    # Enable sandbox
    "SANDBOX_INCLUDE_PKG_MANAGERS": "false",     # Keep in /tools/
    "SANDBOX_INIT_COMMANDS": "mkdir /workspace/data; git clone https://...",
}
```

**Format:**
- `SANDBOX_ENABLE`: "true" or "false"
- `SANDBOX_INCLUDE_PKG_MANAGERS`: "true" or "false"
- `SANDBOX_INIT_COMMANDS`: Semicolon-separated commands

## Usage Examples

### Example 1: Basic Sandboxed Environment

```python
import subprocess
import sys
import os

# Launch server with sandbox enabled
port = "8004"
openenv_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "envs.coding_env.server.app:app",
     "--host", "0.0.0.0", "--port", port],
    env={
        **os.environ,
        "PYTHONPATH": "src",
        "SANDBOX_ENABLE": "true",
        "SANDBOX_INCLUDE_PKG_MANAGERS": "false",
    },
    cwd="/path/to/OpenEnv",
)

# Wait for server, then connect
from envs.coding_env import CodingEnv, ShellAction

client = CodingEnv(base_url=f"http://localhost:{port}")
client.reset()  # Creates fresh sandbox

# Execute commands (isolated in sandbox)
result = client.step(ShellAction(command="ls -la /"))
print(result.observation.stdout)  # Only sees sandbox root

# Cleanup
openenv_process.terminate()
```

### Example 2: With Init Hooks (Git Clone)

```python
# Launch with git clone in init
init_commands = [
    "mkdir -p /workspace",
    "cd /workspace"
]

openenv_process = subprocess.Popen(
    [...],
    env={
        **os.environ,
        "SANDBOX_ENABLE": "true",
        "SANDBOX_INIT_COMMANDS": "; ".join(init_commands),
    },
)

# After reset(), workspace is already set up
client.reset()
result = client.step(ShellAction(command="ls /workspace"))
# Workspace ready!
```

### Example 3: Agent Opts-In to Package Managers

```python
client.reset()

# Package managers NOT in PATH by default
result = client.step(ShellAction(command="git --version"))
# exit_code != 0 (git not found)

# Agent discovers tools directory
result = client.step(ShellAction(command="ls /tools/"))
# Shows: git, curl, wget, apt, etc.

# Agent opts-in by copying
client.step(ShellAction(command="cp /tools/git /usr/bin/git"))

# Now git is available
result = client.step(ShellAction(command="git --version"))
# exit_code == 0 (works!)
```

### Example 4: Fresh Sandbox Each Episode

```python
# Episode 1
client.reset()
client.step(ShellAction(command="echo 'data' > /workspace/file.txt"))
result = client.step(ShellAction(command="cat /workspace/file.txt"))
print(result.observation.stdout)  # "data"

# Episode 2 - fresh sandbox
client.reset()
result = client.step(ShellAction(command="cat /workspace/file.txt"))
# exit_code != 0 (file doesn't exist - fresh sandbox!)
```

## Security Benefits

### 1. Filesystem Isolation
- Agent cannot access host `/home`, `/etc`, `/var`
- Cannot modify host system files
- Damage contained to disposable sandbox

### 2. Package Manager Separation
- Network tools not in PATH by default
- Agent must explicitly opt-in
- RL reward shaping can penalize enabling dangerous tools

### 3. Resource Limits (Docker)
Since sandbox runs in Docker container, add container-level limits:

```bash
docker run \
  --memory="512m" \
  --cpus="1.0" \
  --pids-limit=100 \
  coding-env:latest
```

### 4. Network Isolation (Optional)
```bash
docker run --network=none coding-env:latest
```

## What's Inside the Sandbox

### Core Binaries (Always Available)
Located in `/bin/` and `/usr/bin/`:
- Shell: `bash`, `sh`
- File ops: `ls`, `cat`, `cp`, `mv`, `rm`, `mkdir`, `touch`, `chmod`
- Text processing: `grep`, `sed`, `awk`, `cut`, `sort`, `uniq`
- Utilities: `echo`, `pwd`, `cd`, `find`, `head`, `tail`, `wc`

### Package Managers (In /tools/)
Located in `/tools/` (agent must opt-in):
- Version control: `git`
- Network: `curl`, `wget`
- Package managers: `apt`, `apt-get`, `pip`, `pip3`, `npm`, `yarn`

### Shared Libraries
Automatically copied to `/lib/` and `/lib64/`:
- All dependencies needed by binaries
- Found via `ldd` analysis

## Technical Implementation

### Sandbox Creation Flow

```python
# When reset() is called:

1. Clean up old sandbox (if exists)
   shutil.rmtree(f"/tmp/sandbox_{old_episode_id}")

2. Create new episode ID
   episode_id = str(uuid.uuid4())

3. Create sandbox directory structure
   /tmp/sandbox_{episode_id}/
   ├── bin/, usr/bin/, lib/, lib64/
   ├── tmp/, workspace/, tools/
   └── etc/, dev/, proc/

4. Copy core binaries to bin/
   bash, ls, cat, etc. → /tmp/sandbox_{episode_id}/bin/

5. Copy package managers to tools/
   git, curl, apt → /tmp/sandbox_{episode_id}/tools/

6. Copy shared libraries
   ldd analysis → copy .so files to lib/

7. Run init_commands (if provided)
   chroot /tmp/sandbox_{episode_id} /bin/bash -c "mkdir /workspace"

8. Create ShellExecutor with chroot_path
   ShellExecutor(chroot_path="/tmp/sandbox_{episode_id}")
```

### Command Execution Flow

```python
# When step(ShellAction(command="ls")) is called:

1. Command received: "ls"

2. ShellExecutor wraps with chroot:
   "chroot /tmp/sandbox_{episode_id} /bin/bash -c 'ls'"

3. Execute via subprocess.Popen()

4. Capture stdout, stderr, exit_code

5. Return CodeObservation
```

## Python Code vs Shell Commands

| Aspect | Python Code | Shell Commands |
|--------|-------------|----------------|
| Isolation | ❌ No chroot | ✅ Chroot isolated |
| Filesystem | Full host access | Sandbox only |
| Libraries | All available | Only copied ones |
| Persistence | Variables persist | Fresh each reset |
| Use Case | Computation, logic | System operations |

**Why Python isn't chrooted:**
- Python needs access to all libraries
- Sandboxing Python requires complex venv setup
- Python code already safe (smolagents isolation)
- Shell is the main security risk

## Troubleshooting

### Issue: Sandbox creation fails

**Symptoms:**
```
Warning: Failed to create sandbox, running without chroot
```

**Solution:**
- Check permissions (chroot needs root or appropriate caps)
- Verify `/tmp/` is writable
- Check disk space

### Issue: Commands not found in sandbox

**Symptoms:**
```
exit_code: 127
stderr: command not found
```

**Solution:**
```python
# Check what's available
client.step(ShellAction(command="ls /bin"))
client.step(ShellAction(command="ls /usr/bin"))
client.step(ShellAction(command="ls /tools"))

# If tool missing, it may not be on host system
```

### Issue: Library errors

**Symptoms:**
```
error while loading shared libraries: libXXX.so.X
```

**Solution:**
- Library copying failed
- Check `ldd` output for binary
- May need to manually add libraries to SandboxManager.CORE_BINARIES

### Issue: Init commands fail silently

**Symptoms:**
Init commands don't seem to run

**Solution:**
```python
# Test init commands manually
result = client.step(ShellAction(command="ls /workspace"))
# Check if init command output exists

# Check for command errors (init logs to stdout/stderr)
```

### Issue: Can still access host files

**Symptoms:**
`ls /home` shows host directories

**Solution:**
- Chroot may not be enabled
- Check `SANDBOX_ENABLE=true`
- Verify sandbox created (check `/tmp/sandbox_*`)

## Performance Considerations

### Sandbox Creation Time
- **First reset()**: 1-3 seconds (binary + library copying)
- **Subsequent resets**: 0.5-1 second (cleanup + create)

### Storage Usage
- Each sandbox: 50-200 MB (depends on binaries + libraries)
- Cleaned up automatically on reset()
- Old sandboxes removed when new episode starts

### Optimization Tips

1. **Reuse binaries**: Share a base sandbox, copy-on-write per episode
2. **Limit init_commands**: Only essential setup
3. **Lazy library copying**: Only copy libs when needed

## RL Training Considerations

### Reward Shaping for Safety

Instead of blocking commands, penalize dangerous ones:

```python
# In your RL training loop
def compute_reward(observation, action):
    base_reward = 0.0
    
    # Check for dangerous patterns
    if isinstance(action, ShellAction):
        dangerous = ['rm -rf /', 'dd if=/dev', 'mkfs']
        if any(d in action.command for d in dangerous):
            base_reward -= 10.0  # Heavy penalty
    
    # Reward successful commands
    if observation.exit_code == 0:
        base_reward += 1.0
    
    return base_reward
```

### Exploration vs Safety

Agent can explore freely, but learns through rewards:
- ✅ Try any command (exploration)
- ✅ Learn dangerous commands have negative rewards
- ✅ Discover safe, effective solutions

### Episode Design

```python
# Typical RL episode structure
client.reset()  # Fresh sandbox

for step in range(max_steps):
    action = agent.get_action(observation)
    
    result = client.step(action)
    observation = result.observation
    
    reward = compute_reward(observation, action)
    done = check_done_condition(observation)
    
    agent.update(observation, action, reward, done)
    
    if done:
        break

# Next episode gets fresh sandbox
```

## Future Enhancements

Potential improvements:

- [ ] Configurable core binary list
- [ ] Network namespace isolation
- [ ] CPU/memory limits per sandbox
- [ ] Persistent volumes across episodes
- [ ] Snapshot/restore sandbox state
- [ ] Multi-sandbox support (parallel agents)
- [ ] Custom init scripts from files

## Related Documentation

- [SHELL_COMMANDS.md](SHELL_COMMANDS.md) - Shell command execution
- [LAUNCH_CODING_ENV.md](LAUNCH_CODING_ENV.md) - How to launch environment
- [Coding Environment README](src/envs/coding_env/README.md) - Environment overview

## Example: Complete RL Training Setup

```python
import subprocess
import sys
import os
from envs.coding_env import CodingEnv, CodeAction, ShellAction

# 1. Launch server with sandbox
port = "8004"
process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", 
     "envs.coding_env.server.app:app", 
     "--host", "0.0.0.0", "--port", port],
    env={
        **os.environ,
        "PYTHONPATH": "src",
        "SANDBOX_ENABLE": "true",
        "SANDBOX_INCLUDE_PKG_MANAGERS": "false",
        "SANDBOX_INIT_COMMANDS": "mkdir -p /workspace/project",
    },
)

# 2. Wait for ready, connect
time.sleep(3)
client = CodingEnv(base_url=f"http://localhost:{port}")

# 3. RL training loop
for episode in range(num_episodes):
    client.reset()  # Fresh sandbox
    
    for step in range(max_steps):
        # Agent decides: Python or Shell?
        if agent.should_use_python():
            action = CodeAction(code=agent.generate_python())
        else:
            action = ShellAction(command=agent.generate_shell())
        
        result = client.step(action)
        
        # Compute reward
        reward = compute_reward(result.observation, action)
        
        # Update agent
        agent.learn(action, reward)

# 4. Cleanup
process.terminate()
```

## License

BSD 3-Clause License - See LICENSE file