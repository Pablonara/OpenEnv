# Chroot Sandbox - Quick Reference

## 🚀 Quick Start

### Launch with Sandbox (Default: Enabled)
```python
import subprocess
import os

process = subprocess.Popen(
    ["python", "-m", "uvicorn", "envs.coding_env.server.app:app", "--port", "8004"],
    env={
        **os.environ,
        "PYTHONPATH": "src",
        "SANDBOX_ENABLE": "true",                # Enable chroot (default)
        "SANDBOX_INCLUDE_PKG_MANAGERS": "false", # Keep in /tools/ (default)
        "SANDBOX_INIT_COMMANDS": "mkdir /workspace; echo 'Ready'",
    },
)
```

### Connect and Use
```python
from envs.coding_env import CodingEnv, ShellAction

client = CodingEnv(base_url="http://localhost:8004")
client.reset()  # Creates fresh sandbox

# Commands run in isolated chroot
result = client.step(ShellAction(command="ls -la /"))
print(result.observation.stdout)
```

---

## 📁 Sandbox Structure

```
/tmp/sandbox_{episode_id}/
├── bin/           ✅ Core utilities (bash, ls, cat, mkdir, etc.)
├── usr/bin/       📦 Empty (agent can add tools here)
├── lib/, lib64/   📚 Auto-copied shared libraries
├── tmp/           💾 Writable temp space
├── workspace/     🏗️  Agent's working directory
└── tools/         🔒 Package managers (git, curl, apt) - OPT-IN ONLY
```

---

## ⚙️ Configuration

### Environment Variables
| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `SANDBOX_ENABLE` | true/false | true | Enable chroot sandbox |
| `SANDBOX_INCLUDE_PKG_MANAGERS` | true/false | false | Put pkg managers in PATH |
| `SANDBOX_INIT_COMMANDS` | "cmd1; cmd2" | "" | Semicolon-separated setup commands |

### SandboxConfig (Server-Side)
```python
from envs.coding_env import SandboxConfig

config = SandboxConfig(
    enable=True,
    init_commands=["mkdir /workspace/project", "cd /workspace"],
    include_package_managers=False  # Security: keep in /tools/
)
```

---

## 🔐 Security Model

### What's Always Available (Core Binaries)
✅ `bash`, `sh`, `ls`, `cat`, `cp`, `mv`, `rm`, `mkdir`, `chmod`  
✅ `grep`, `sed`, `awk`, `find`, `head`, `tail`, `sort`, `cut`  
✅ `echo`, `pwd`, `cd`, `touch`, `wc`, `uniq`, `tr`

### What's Opt-In Only (/tools/)
🔒 `git`, `curl`, `wget`, `apt`, `apt-get`, `pip`, `npm`, `yarn`

**Why?** Network tools require explicit agent decision (security + RL reward shaping)

---

## 💡 Common Patterns

### Pattern 1: Basic Isolated Execution
```python
client.reset()  # Fresh sandbox
result = client.step(ShellAction(command="mkdir /workspace/data"))
result = client.step(ShellAction(command="echo 'test' > /workspace/data/file.txt"))
result = client.step(ShellAction(command="cat /workspace/data/file.txt"))
```

### Pattern 2: Agent Opts-In to Package Manager
```python
client.reset()

# Git NOT available by default
result = client.step(ShellAction(command="git --version"))
# exit_code != 0

# Agent discovers tools
result = client.step(ShellAction(command="ls /tools/"))
# Shows: git, curl, wget, etc.

# Agent opts-in
client.step(ShellAction(command="cp /tools/git /usr/bin/git"))

# Now git works
result = client.step(ShellAction(command="git --version"))
# exit_code == 0
```

### Pattern 3: Init Hooks (Workspace Setup)
```python
# Launch with init commands
env = {
    "SANDBOX_INIT_COMMANDS": "mkdir -p /workspace/project; cd /workspace"
}

# After reset(), workspace ready
client.reset()
result = client.step(ShellAction(command="pwd"))
# Shows: /workspace
```

### Pattern 4: Fresh Sandbox Per Episode
```python
# Episode 1
client.reset()
client.step(ShellAction(command="echo 'data' > /tmp/file.txt"))

# Episode 2 - Fresh sandbox!
client.reset()
result = client.step(ShellAction(command="cat /tmp/file.txt"))
# exit_code != 0 (file doesn't exist - new sandbox)
```

---

## 🎯 RL Training Tips

### Reward Shaping (Don't Block, Penalize)
```python
def compute_reward(action, observation):
    reward = 0.0
    
    # Success bonus
    if observation.exit_code == 0:
        reward += 1.0
    
    # Penalty for dangerous patterns (agent can still try)
    if isinstance(action, ShellAction):
        if 'rm -rf /' in action.command:
            reward -= 10.0
        if 'cp /tools/' in action.command:
            reward -= 2.0  # Discourage opt-in to network tools
    
    return reward
```

### Episode Structure
```python
for episode in range(num_episodes):
    client.reset()  # Fresh isolated sandbox
    
    for step in range(max_steps):
        action = agent.get_action(observation)
        result = client.step(action)
        reward = compute_reward(action, result.observation)
        agent.learn(action, reward, result.observation)
```

---

## 🔍 Python vs Shell

| Aspect | Python Code | Shell Commands |
|--------|-------------|----------------|
| Isolation | ❌ No chroot | ✅ Chroot jail |
| Filesystem | Full host | Sandbox only |
| Use Case | Computation | System ops |
| Persistence | Vars persist | Fresh on reset |

**Note:** Python bypasses chroot (needs full library access)

---

## 🐛 Troubleshooting

### Command Not Found
```bash
# Check what's available
ls /bin
ls /usr/bin
ls /tools
```

### Sandbox Creation Failed
```bash
# Check permissions (needs root or Docker caps)
# Check /tmp/ is writable
# Check disk space
```

### Library Errors
```bash
# "error while loading shared libraries"
# Some binaries may need manual lib additions
# Check SandboxManager.CORE_BINARIES
```

### Can Access Host Files
```bash
# Sandbox may not be enabled
# Check SANDBOX_ENABLE=true
# Verify /tmp/sandbox_* exists
```

---

## 📊 Performance

| Operation | Time | Storage |
|-----------|------|---------|
| First reset() | 1-3s | 50-200 MB |
| Subsequent resets | 0.5-1s | Same |
| Cleanup | Automatic | Per episode |

---

## 🧪 Testing

```bash
# Test basic executor
python examples/test_shell_executor_simple.py

# Test full sandbox
python examples/test_sandbox_with_init.py

# Test with shell commands
python examples/test_coding_with_shell.py
```

---

## 📚 Documentation

- **[SANDBOX_CHROOT.md](SANDBOX_CHROOT.md)** - Full documentation (514 lines)
- **[SHELL_COMMANDS.md](SHELL_COMMANDS.md)** - Shell command guide
- **[LAUNCH_CODING_ENV.md](LAUNCH_CODING_ENV.md)** - Launch like 2048 example

---

## ✨ Key Takeaways

✅ **Chroot isolates filesystem** - Agent can't damage host  
✅ **Core binaries always available** - Agent can explore freely  
✅ **Package managers opt-in** - Security by default  
✅ **Init hooks** - Custom workspace setup  
✅ **Fresh per episode** - No state pollution  
✅ **RL-friendly** - Learn through rewards, not restrictions  

**Perfect for RL training where agents need flexibility + safety!** 🎉