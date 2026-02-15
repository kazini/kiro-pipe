# Startup Window Feature

## Overview
Usage limits are now blocked for the first 5 seconds after the proxy starts. This ensures Kiro doesn't check usage limits before custom models are injected.

## Why This Is Needed

### The Problem
1. Kiro starts and immediately checks usage limits
2. Model injection happens in the response to `/ListAvailableModels`
3. If usage limits are checked before models are injected, `custom_model_ids` is empty
4. Result: Usage limits are NOT blocked when they should be

### The Solution
Block usage limits for the first 5 seconds after proxy starts, giving model injection time to complete.

## Implementation

### Code Changes

**Location**: `kiropipe.py`

#### 1. Added start time tracker (line ~237)
```python
def __init__(self):
    # ... other initialization ...
    self.start_time = time.time()  # Track when proxy started
```

#### 2. Updated usage limits check (lines ~270-280)
```python
if 'getUsageLimits' in flow.request.path:
    elapsed_time = time.time() - self.start_time
    within_startup_window = elapsed_time < 5.0
    should_block = len(self.custom_model_ids) > 0 or within_startup_window
    
    if DEBUG_MODE_ENABLED:
        print(f"  Elapsed time: {elapsed_time:.2f}s")
        print(f"  Within startup window (5s): {within_startup_window}")
        print(f"  Should block: {should_block}")
```

#### 3. Updated blocking reason (lines ~285-290)
```python
if should_block:
    if within_startup_window:
        print(f"  Reason: Within startup window ({elapsed_time:.2f}s / 5.0s)")
    else:
        print(f"  Reason: Custom models available ({len(self.custom_model_ids)} models)")
```

## Behavior

### Timeline

```
0.0s - Proxy starts
     - self.start_time = time.time()
     
0.1s - Kiro checks usage limits
     - elapsed_time = 0.1s
     - within_startup_window = True
     - should_block = True
     - Reason: "Within startup window (0.10s / 5.0s)"
     
0.5s - Kiro requests /ListAvailableModels
     - Models are injected
     - custom_model_ids populated
     
1.0s - Kiro checks usage limits again
     - elapsed_time = 1.0s
     - within_startup_window = True
     - should_block = True
     - Reason: "Within startup window (1.00s / 5.0s)"
     
5.1s - Kiro checks usage limits
     - elapsed_time = 5.1s
     - within_startup_window = False
     - custom_model_ids has models
     - should_block = True
     - Reason: "Custom models available (2 models)"
     
10.0s - Kiro checks usage limits
      - elapsed_time = 10.0s
      - within_startup_window = False
      - custom_model_ids has models
      - should_block = True
      - Reason: "Custom models available (2 models)"
```

### Blocking Logic

Usage limits are blocked if:
- **Within first 5 seconds** (startup window), OR
- **Custom models exist** (after injection)

```python
should_block = len(self.custom_model_ids) > 0 or within_startup_window
```

## Debug Output

### Within Startup Window (< 5 seconds)
```
[USAGE LIMITS CHECK]
  Elapsed time: 0.50s
  Within startup window (5s): True
  Custom model IDs: set()
  Count: 0
  Should block: True
 [BLOCKED USAGE LIMITS] https://q.us-east-1.amazonaws.com/getUsageLimits?...
  Reason: Within startup window (0.50s / 5.0s)
```

### After Startup Window (> 5 seconds)
```
[USAGE LIMITS CHECK]
  Elapsed time: 10.25s
  Within startup window (5s): False
  Custom model IDs: {'test-dummy-1', 'test-dummy-2'}
  Count: 2
  Should block: True
 [BLOCKED USAGE LIMITS] https://q.us-east-1.amazonaws.com/getUsageLimits?...
  Reason: Custom models available (2 models)
```

### After Startup Window (No Custom Models)
```
[USAGE LIMITS CHECK]
  Elapsed time: 10.25s
  Within startup window (5s): False
  Custom model IDs: set()
  Count: 0
  Should block: False
```

## Testing

### Test 1: Verify Startup Window Blocking
1. Enable debug mode
2. Run kiropipe.py
3. Watch for usage limits checks in first 5 seconds

**Expected**: All checks within 5 seconds are blocked with reason "Within startup window"

### Test 2: Verify Transition After 5 Seconds
1. Enable debug mode
2. Run kiropipe.py
3. Wait for usage limits check after 5 seconds

**Expected**: 
- If custom models exist: Blocked with reason "Custom models available"
- If no custom models: Not blocked

### Test 3: Verify Model Injection Still Works
1. Enable debug mode
2. Run kiropipe.py
3. Check model injection output

**Expected**: Models are injected normally, startup window doesn't interfere

## Benefits

✓ **Prevents Race Condition**: Usage limits can't be checked before models are injected
✓ **Graceful Startup**: Gives system time to initialize
✓ **Clear Debugging**: Shows elapsed time and reason for blocking
✓ **Automatic Transition**: After 5 seconds, switches to normal blocking logic
✓ **No Configuration Needed**: Works automatically

## Edge Cases

### Case 1: Kiro Checks Usage Limits Multiple Times
**Behavior**: All checks within 5 seconds are blocked
**Result**: ✓ Correct

### Case 2: Model Injection Takes Longer Than 5 Seconds
**Behavior**: After 5 seconds, blocking depends on custom_model_ids
**Result**: ✓ Correct (models will be injected by then)

### Case 3: No Custom Models Configured
**Behavior**: After 5 seconds, usage limits are NOT blocked
**Result**: ✓ Correct (Kiro models should have normal limits)

### Case 4: Proxy Restart
**Behavior**: Timer resets, 5-second window starts again
**Result**: ✓ Correct

## Configuration

No configuration needed! The 5-second window is hardcoded and works automatically.

To change the duration, modify this line in `kiropipe.py`:
```python
within_startup_window = elapsed_time < 5.0  # Change 5.0 to desired seconds
```

## Summary

- Usage limits are blocked for first 5 seconds after proxy starts
- Prevents race condition where usage limits are checked before model injection
- After 5 seconds, normal blocking logic applies (based on custom_model_ids)
- Debug output shows elapsed time and blocking reason
- No configuration needed, works automatically
