# KiroPipe Changelog

## [Current] - 2026-02-15

### Fixed
1. **"Kiro Closed" message appearing immediately**
   - Changed from `subprocess.run()` (blocking) to `subprocess.Popen()` (non-blocking)
   - Now monitors Kiro process continuously
   - Only shows "Kiro closed" when process actually terminates

2. **Script not closing when Kiro closes**
   - Added process monitoring loop
   - Detects when Kiro.exe terminates
   - Automatically terminates proxy and exits script
   - Clean shutdown with `sys.exit(0)`

3. **Crash when another Kiro instance is running**
   - Added `kill_existing_kiro()` function
   - Checks for existing Kiro.exe processes using `tasklist`
   - Terminates existing instances with `taskkill /F`
   - Waits 1 second before launching new instance
   - Prevents conflicts and crashes

### Added
- Process monitoring loop that checks both Kiro and proxy status
- Automatic cleanup when either process terminates
- Better error handling for process management
- Graceful shutdown on Ctrl+C

### Technical Details

**Before:**
```python
subprocess.run([kiro_exe, ...])  # Blocking - waits for Kiro to close
print("Kiro closed")  # Shows immediately after launch
```

**After:**
```python
process = subprocess.Popen([kiro_exe, ...])  # Non-blocking
while True:
    if process.poll() is not None:  # Check if still running
        print("Kiro closed")  # Only when actually closed
        break
```

**Process Management:**
```python
def kill_existing_kiro():
    # Check for existing processes
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Kiro.exe'])
    if 'Kiro.exe' in result.stdout:
        # Terminate existing instances
        subprocess.run(['taskkill', '/F', '/IM', 'Kiro.exe'])
        time.sleep(1)
```

**Cleanup on Exit:**
```python
# When Kiro closes, terminate proxy
if proxy_process.poll() is None:
    proxy_process.terminate()
    proxy_process.wait()
sys.exit(0)
```

## Previous Changes

### Project Restructure
- Organized files into `_kiropipe/engine/` and `_kiropipe/tools/`
- Core functionality in `engine/`, development tools in `tools/`
- All scripts use relative paths from their locations

### AWS Event Stream Encoder
- Implemented complete encoder matching AWS Q format
- All tests passing
- Verified against captured responses

### Configuration System
- Added `DEBUG_MODE` flag
- Added blocking flags (telemetry, updates, usage limits)
- Configurable paths and ports
- Auto-detect Kiro.exe location
