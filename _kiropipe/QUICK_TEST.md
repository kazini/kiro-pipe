# Quick Test Guide - Model Discovery

## What We're Testing
Whether Kiro has a hardcoded or dynamic model list.

## Quick Start

### 1. Run KiroPipe
```bash
python kiropipe.py
```

### 2. Use Kiro
- Open Kiro (it should launch automatically)
- Look for model selection (dropdown, settings, chat interface)
- Try to switch between models
- Send a few messages

### 3. Watch Console
Look for **MAGENTA** colored alerts like this:

```
============================================================
 [MODEL-RELATED ENDPOINT DETECTED]
============================================================
Path: /getAvailableModels
Method: GET
URL: https://q.us-east-1.amazonaws.com/getAvailableModels
============================================================
```

## What the Results Mean

### ✅ If you see MAGENTA alerts:
**Kiro fetches models dynamically!**

Next steps:
1. Note the endpoint path (e.g., `/getAvailableModels`)
2. Run: `python _kiropipe/devtools/test_model_injection.py`
3. We'll inject fake models to test if Kiro accepts them

### ❌ If you see NO alerts:
**Kiro has hardcoded models**

Next steps:
1. We'll use model replacement strategy
2. Intercept model selection in requests
3. Route to custom backends transparently

## Common Model-Related Endpoints

Watch for these paths:
- `/getAvailableModels`
- `/listModels`
- `/modelConfiguration`
- `/configuration`
- `/models`
- `/selectModel`

## Troubleshooting

**Q: I don't see any MAGENTA alerts**
- Make sure you're actually switching models in Kiro
- Check if Kiro has a model selection UI
- Try opening settings/preferences
- Models might be hardcoded (this is OK, we have a strategy for this)

**Q: I see alerts but they're not model-related**
- The keywords are broad to catch variations
- Look at the actual path to confirm
- We're looking for paths with: model, list, available, configuration

**Q: Kiro won't launch**
- Check that Kiro.exe is in the correct location
- Verify proxy port (29974) is not in use
- Check console for error messages

## After Discovery

### If Dynamic (endpoint found):
```bash
# Generate test injections
python _kiropipe/devtools/test_model_injection.py

# This creates test files in:
# _kiropipe/debug_logs/model_tests/

# Follow instructions in INSTRUCTIONS.txt
```

### If Hardcoded (no endpoint):
We'll implement model replacement:
- User selects "Claude Sonnet" in Kiro
- We detect this in the request
- We route to our custom model
- User gets custom model response
- Kiro thinks it's still using Claude

## Debug Mode (Optional)

For more detailed logging, enable debug mode:

Edit `_kiropipe/kiropipe_config.yaml`:
```yaml
debug:
  debug_mode_enabled: true
  store_interaction_blocks: true
```

This will:
- Log ALL requests/responses
- Save traffic to files
- Show detailed headers and bodies

## Questions?

See:
- `MODEL_TESTING_PLAN.md` - Detailed testing plan
- `KIRO-PIPE_DEV_JOURNAL.md` - Phase 12 for background
- `devtools/test_model_injection.py` - Injection tool
- `devtools/discover_endpoints.py` - Traffic analyzer
