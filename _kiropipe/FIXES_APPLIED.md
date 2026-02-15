# Fixes Applied

## Issue 1: Kiro Models Still Using "Credit"
**Problem**: Kiro's original models were not being modified to use "Kiro Credits"

**Solution**: Added code to modify Kiro's models when they're first loaded
```python
# Change Kiro's rateUnit from "Credit" to "Kiro Credits"
if model.get('rateUnit') == 'Credit':
    model['rateUnit'] = 'Kiro Credits'
```

**Location**: `kiropipe.py` line ~533

**Result**: 
- Kiro models: `"rateUnit": "Kiro Credits"`
- Config models: `"rateUnit": 0`
- Dummy models: `"rateUnit": "Credit"` (unchanged)

---

## Issue 2: Duplicate Dependency Checks
**Problem**: Dependencies were being checked multiple times:
1. At script load (first time)
2. After config load
3. When mitmproxy reloads the script

This resulted in output like:
```
Checking dependencies...
All dependencies satisfied.
[Config] Loaded from ...
Checking dependencies...
All dependencies satisfied.
[14:56:47.746] Loading script ...
Checking dependencies...
All dependencies satisfied.
[Config] Loaded from ...
Checking dependencies...
All dependencies satisfied.
```

**Solution**: Added a global flag to ensure dependencies are only checked once per process
```python
# Global flag to prevent duplicate dependency checks
_DEPENDENCIES_CHECKED = False

def check_dependencies_once():
    """Check dependencies only once per process"""
    global _DEPENDENCIES_CHECKED
    if not _DEPENDENCIES_CHECKED:
        check_dependencies()
        _DEPENDENCIES_CHECKED = True
```

**Location**: `kiropipe.py` lines ~145-154

**Result**: Dependencies are now checked only once:
```
Checking dependencies...
All dependencies satisfied.
[Config] Loaded from ...
============================================================
KiroPipe - Unified Launcher
============================================================
```

---

## Summary of Changes

### File: `kiropipe.py`

#### Change 1: Added dependency check flag (lines ~145-154)
```python
# Global flag to prevent duplicate dependency checks
_DEPENDENCIES_CHECKED = False

def check_dependencies_once():
    """Check dependencies only once per process"""
    global _DEPENDENCIES_CHECKED
    if not _DEPENDENCIES_CHECKED:
        check_dependencies()
        _DEPENDENCIES_CHECKED = True

# Check dependencies before importing anything else
check_dependencies_once()
```

#### Change 2: Removed second dependency check (line ~203)
```python
# REMOVED: check_dependencies()
```

#### Change 3: Modified Kiro models rateUnit (lines ~530-536)
```python
# Track Kiro's original model IDs and modify their rateUnit
if 'models' in response_data:
    for model in response_data['models']:
        self.kiro_model_ids.add(model.get('modelId'))
        # Change Kiro's rateUnit from "Credit" to "Kiro Credits"
        if model.get('rateUnit') == 'Credit':
            model['rateUnit'] = 'Kiro Credits'
```

---

## Model rateUnit Summary

| Model Type | rateMultiplier | rateUnit | Example |
|------------|----------------|----------|---------|
| Kiro | Number (1.0, 1.3, etc.) | "Kiro Credits" | `1.3, "Kiro Credits"` |
| Config | Provider name (uppercase) | 0 | `"ANTHROPIC", 0` |
| Dummy | Number (from JSON) | "Credit" | `1.0, "Credit"` |

---

## Testing

### Test 1: Verify Kiro Models Use "Kiro Credits"
1. Enable debug mode
2. Run kiropipe.py
3. Check model injection output

**Expected Output**:
```
Modified Kiro models rateUnit to 'Kiro Credits'
```

**API Response**:
```json
{
  "modelId": "claude-sonnet-4.5",
  "rateUnit": "Kiro Credits"
}
```

### Test 2: Verify Single Dependency Check
1. Run kiropipe.py
2. Check console output

**Expected Output** (only one check):
```
Checking dependencies...
All dependencies satisfied.

[Config] Loaded from ...

============================================================
KiroPipe - Unified Launcher
============================================================
```

**NOT** (multiple checks):
```
Checking dependencies...
All dependencies satisfied.
[Config] Loaded from ...
Checking dependencies...
All dependencies satisfied.
```

---

## Verification

Run the following to verify:
```bash
python kiropipe.py
```

Look for:
1. Only ONE "Checking dependencies..." message
2. Debug output showing "Modified Kiro models rateUnit to 'Kiro Credits'"
3. No duplicate config loading messages

---

## Files Modified
- `kiropipe.py`: Added flag, removed duplicate check, modified Kiro models

## Files NOT Modified
- `_kiropipe/devtools/dummy_models.json`: Left unchanged as requested
