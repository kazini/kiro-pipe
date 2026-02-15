# Visual Changes Guide

## Console Output Changes

### Dependency Check (Now Appears Twice)

**Before**:
```
Checking dependencies...
All dependencies satisfied.

[Config] Loaded from ...

============================================================
KiroPipe - Unified Launcher
============================================================
```

**After**:
```
Checking dependencies...
All dependencies satisfied.

[Config] Loaded from ...

Checking dependencies...
All dependencies satisfied.

============================================================
KiroPipe - Unified Launcher
============================================================
```

---

## Model Injection Output (Debug Mode)

### Config Models

**Before**:
```
============================================================
[INJECTING CUSTOM MODELS]
============================================================
Original Kiro models: 7
Tracked Kiro model IDs: 7
Injected 2 custom model(s):
  - Claude 3 Opus
  - GPT-4
Total models: 9
============================================================
```

**After** (same visual, but models have different internal structure):
```
============================================================
[INJECTING CUSTOM MODELS]
============================================================
Original Kiro models: 7
Tracked Kiro model IDs: 7
Injected 2 custom model(s):
  - Claude 3 Opus
  - GPT-4
Total models: 9
============================================================
```

**Internal Change** (not visible in console, but in API response):
```json
// Before
{
  "modelId": "claude-3-opus",
  "rateMultiplier": 1.0,
  "rateUnit": "Credit"
}

// After
{
  "modelId": "claude-3-opus",
  "rateMultiplier": "ANTHROPIC",
  "rateUnit": 0
}
```

---

### Dummy Models with Field Stripping

**New Output**:
```
============================================================
[INJECTING CUSTOM MODELS]
============================================================
Original Kiro models: 7
Tracked Kiro model IDs: 7
[STRIP] Removed non-schema fields from test-dummy-1: provider, custom_field, endpoint
[STRIP] Removed non-schema fields from test-dummy-2: api_key, internal_note
[OVERRIDE] Replaced Kiro model: auto (inherits Kiro type)
[STRIP] Removed non-schema fields from auto: override_test, metadata
Loaded 3 dummy test model(s)
Injected 3 custom model(s):
  - Test Dummy 1
  - Test Subject Beta (2)
  - Auto (OVERRIDDEN) (override)
Total models: 9
============================================================
```

---

## Model List in Kiro UI

### Before (All Models Look Similar)
```
┌─────────────────────────────────┐
│ Model Selector                  │
├─────────────────────────────────┤
│ ○ Auto                          │
│ ○ Claude Sonnet 4.5             │
│ ○ Claude 3 Opus                 │  ← Config model (looks same)
│ ○ GPT-4                         │  ← Config model (looks same)
│ ○ Test Dummy 1                  │  ← Dummy model (looks same)
└─────────────────────────────────┘
```

### After (Internal Distinction)
```
┌─────────────────────────────────┐
│ Model Selector                  │
├─────────────────────────────────┤
│ ○ Auto                          │  ← rateMultiplier: 1.0, rateUnit: "Credit"
│ ○ Claude Sonnet 4.5             │  ← rateMultiplier: 1.3, rateUnit: "Credit"
│ ○ Claude 3 Opus                 │  ← rateMultiplier: "ANTHROPIC", rateUnit: 0
│ ○ GPT-4                         │  ← rateMultiplier: "LITELLM", rateUnit: 0
│ ○ Test Dummy 1                  │  ← rateMultiplier: 1.0, rateUnit: "Credit"
└─────────────────────────────────┘
```

**Note**: Visual appearance in Kiro UI is the same, but internal data structure differs.

---

## API Response Comparison

### Kiro Model (Unchanged)
```json
{
  "modelId": "claude-sonnet-4.5",
  "modelName": "Claude Sonnet 4.5",
  "description": "The latest Claude Sonnet model",
  "promptCaching": {
    "maximumCacheCheckpointsPerRequest": 4,
    "minimumTokensPerCacheCheckpoint": 1024,
    "supportsPromptCaching": true
  },
  "rateMultiplier": 1.3,
  "rateUnit": "Credit",
  "supportedInputTypes": ["TEXT", "IMAGE"],
  "tokenLimits": {
    "maxInputTokens": 200000,
    "maxOutputTokens": null
  }
}
```

### Config Model (Changed)
```json
{
  "modelId": "claude-3-opus",
  "modelName": "Claude 3 Opus",
  "description": "Custom anthropic model",
  "promptCaching": {
    "maximumCacheCheckpointsPerRequest": 4,
    "minimumTokensPerCacheCheckpoint": 1024,
    "supportsPromptCaching": true
  },
  "rateMultiplier": "ANTHROPIC",  // ← Changed from 1.0
  "rateUnit": 0,                   // ← Changed from "Credit"
  "supportedInputTypes": ["TEXT", "IMAGE"],
  "tokenLimits": {
    "maxInputTokens": 200000,
    "maxOutputTokens": null
  }
}
```

### Dummy Model (Cleaned)
```json
// Input (dummy_models.json)
{
  "modelId": "test-dummy-1",
  "modelName": "Test Dummy 1",
  "description": "First test model",
  "rateMultiplier": 1.0,
  "rateUnit": "Credit",
  "provider": "test-provider",      // ← Extra field
  "custom_field": "should strip",   // ← Extra field
  "endpoint": "https://example.com" // ← Extra field
}

// Output (API response)
{
  "modelId": "test-dummy-1",
  "modelName": "Test Dummy 1",
  "description": "First test model",
  "rateMultiplier": 1.0,
  "rateUnit": "Credit"
  // Extra fields removed
}
```

---

## Color-Coded Console Output

### Field Stripping (Yellow)
```
[STRIP] Removed non-schema fields from test-dummy-1: provider, custom_field, endpoint
```

### Override (Magenta)
```
[OVERRIDE] Replaced Kiro model: auto (inherits Kiro type)
```

### Model Injection (Cyan)
```
Loaded 3 dummy test model(s)
Injected 3 custom model(s):
  - Test Dummy 1
  - Test Subject Beta (2)
  - Auto (OVERRIDDEN) (override)
```

---

## Quick Reference

| Model Type | rateMultiplier | rateUnit | Example |
|------------|----------------|----------|---------|
| Kiro | Number (1.0, 1.3, etc.) | "Credit" | `1.3, "Credit"` |
| Config | Provider name (uppercase) | 0 | `"ANTHROPIC", 0` |
| Dummy | Number (from JSON) | "Credit" | `1.0, "Credit"` |

---

## Benefits Summary

✓ **Easy Identification**: Provider name shows model source
✓ **Clear Distinction**: rateUnit=0 marks config models
✓ **Flexible Metadata**: Extra fields in dummy models don't break injection
✓ **Better Debugging**: Field stripping is logged
✓ **Robust Loading**: Second dependency check ensures stability
