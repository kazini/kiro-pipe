# Spawn Gating Testing Guide

## Quick Start

The spawn gating functionality is now integrated into `attach.py`. This allows you to start Kiro with Frida hooks from the very beginning, bypassing anti-debug protection.

## Single Command Testing

### Option 1: Use the batch file (Windows)
```bash
cd frida-scripts
test_spawn.bat
```

### Option 2: Direct Python command
```bash
cd frida-scripts
python attach.py --spawn --hook kiro_api_hook
```

### Option 3: With custom Kiro path
```bash
python attach.py --spawn --hook kiro_api_hook --kiro-path "C:\Custom\Path\Kiro.exe"
```

## What to Expect

### Successful Output Should Show:

```
🚀 Frida Spawn Gating Mode
============================================================

Kiro path: C:\Users\...\Kiro.exe
Hook: kiro_api_hook

[1/5] Loading hook script...
✓ Loaded kiro_api_hook.js

[2/5] Spawning Kiro (suspended)...
✓ Spawned with PID: 12345

[3/5] Attaching to spawned process...
✓ Attached to PID 12345

[4/5] Injecting hooks (before resume)...
✓ Hooks injected successfully

[5/5] Resuming Kiro...
✓ Kiro is now running with hooks active
Main PID: 12345

============================================================
✓ SPAWN GATING ACTIVE - MONITORING CHILD PROCESSES
============================================================

Monitoring for child processes (network subprocess)...
Press Ctrl+C to stop

[NEW PROCESS] PID 12346: Kiro.exe
  Attempting to attach...
  ✓ Hooks injected into PID 12346

[NEW PROCESS] PID 12347: Kiro.exe
  Attempting to attach...
  ✗ Failed to attach to PID 12347: process refused to load frida-agent

[HOOK] Searching for AWS Q endpoints...
[HOOK] Found module: index.node (59.4 MB)
[API] Detected AWS Q request: https://q.us-east-1.amazonaws.com/...
```

## Key Success Indicators

1. ✅ **Kiro spawns successfully** - Main process starts
2. ✅ **Hooks inject before resume** - Timing is critical
3. ✅ **Child processes detected** - Network subprocess appears
4. ✅ **At least one child accepts hooks** - Network process hooked
5. ✅ **API calls detected** - Hook is working

## Expected Failures (Normal)

- Some child processes will refuse Frida (renderer processes with anti-debug)
- This is expected - we only need the networking process
- Look for at least ONE successful child process hook

## Troubleshooting

### "Could not find Kiro.exe"
Specify path manually:
```bash
python attach.py --spawn --kiro-path "C:\Path\To\Kiro.exe"
```

### "Failed to spawn"
- Check if Kiro is already running (close it first)
- Verify Kiro.exe path is correct
- Run as administrator if needed

### "Failed to inject hooks"
- Check if hook file exists: `kiro_api_hook.js`
- Try different hook: `--hook test_any_network`

### No child processes detected
- Wait longer (can take 5-10 seconds)
- Kiro might be slow to spawn subprocesses
- Check Task Manager for multiple Kiro.exe processes

## Available Hooks

- `kiro_api_hook` - AWS Q endpoint detection (recommended)
- `test_any_network` - Generic network monitoring
- `chromium_network_hook` - Chromium internals
- `socket_intercept` - Socket-level hooking
- `diagnose_networking` - Full diagnostic output

## Next Steps After Successful Hook

1. Interact with Kiro (trigger API calls)
2. Watch console for intercepted requests
3. Verify AWS Q endpoints are detected
4. Check if certificate validation can be bypassed

## Comparison: Spawn vs Attach

### Spawn Mode (--spawn)
- ✅ Hooks before anti-debug initializes
- ✅ Can hook renderer processes
- ✅ Auto-detects child processes
- ❌ Requires Kiro to be closed first

### Attach Mode (default)
- ✅ Works on running Kiro
- ✅ Faster for testing
- ❌ Anti-debug already active
- ❌ Renderer processes refuse hooks

## Testing Checklist

- [ ] Run `test_spawn.bat` or direct command
- [ ] Verify Kiro spawns successfully
- [ ] Confirm hooks inject before resume
- [ ] Wait for child processes (5-10 seconds)
- [ ] Check for at least one successful child hook
- [ ] Interact with Kiro to trigger API calls
- [ ] Look for AWS Q endpoint detection in output
- [ ] Document which PIDs accept/refuse hooks
- [ ] Note any error messages or failures

## Success Criteria

The spawn gating is working if:
1. Kiro starts with hooks active
2. At least one child process accepts hooks
3. Network activity is detected/logged
4. No immediate crashes or errors

Even if some processes refuse hooks, as long as the networking subprocess accepts them, we've succeeded in bypassing the anti-debug protection for that critical process.
