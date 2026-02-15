# Test Fake Model Injection

## What We're Testing
Whether Kiro will display a fake model we inject into the `/ListAvailableModels` response.

## Status
✅ Endpoint discovered: `/ListAvailableModels`
✅ Injection code added to `kiropipe.py`
⏳ Awaiting test results

## How to Test

### 1. Restart KiroPipe
```bash
python kiropipe.py
```

### 2. Watch Console Output
You should see:
```
============================================================
 [INTERCEPTING MODEL LIST]
============================================================
Testing if Kiro accepts custom models...
```

Then when the response comes back:
```
============================================================
 [MODIFYING MODEL LIST]
============================================================
Original models: X
✓ Injected fake model: 🧪 TEST Custom Model
New model count: X+1
============================================================
✓ Model list modified!
Check Kiro's model selector for: '🧪 TEST Custom Model'
============================================================
```

### 3. Check Kiro's Model Selector
Look for the model selector in Kiro (usually in chat interface or settings).

**What to look for:**
- A model named: "🧪 TEST Custom Model"
- With emoji: 🧪
- Description: "Fake model to test dynamic loading"

## Expected Results

### ✅ SUCCESS: Fake model appears
**Meaning:** Kiro has a DYNAMIC model list!

**What this enables:**
- We can inject our custom models (Anthropic, OpenAI, Ollama, etc.)
- Users can select them from Kiro's UI
- No need to replace existing models

**Next steps:**
1. Remove test model
2. Inject real custom models from config
3. Map selections to our bridge server

### ❌ FAILURE: Fake model doesn't appear
**Possible reasons:**
1. Response format is not JSON (might be AWS Event Stream)
2. Kiro validates models against a whitelist
3. Additional fields required
4. Model structure is different

**Next steps:**
1. Enable debug mode to see actual response format
2. Run `python _kiropipe/devtools/capture_model_list.py`
3. Adjust injection code based on actual format
4. Try different model structures

## Troubleshooting

### Console shows "Response is not JSON"
The response might be in AWS Event Stream format.

**Fix:**
1. Enable debug mode and store_interaction_blocks
2. Capture the actual response
3. Use our Event Stream decoder to parse it
4. Modify injection code to use Event Stream encoding

### Console shows "Response structure: [...]"
The JSON structure is different than expected.

**Fix:**
1. Note the actual keys shown
2. Adjust the injection code to match
3. Try injecting into the correct key

### No console output at all
The interception might not be working.

**Check:**
1. Is kiropipe.py running?
2. Is Kiro using the proxy?
3. Did the `/ListAvailableModels` request happen?
4. Try restarting Kiro to trigger a fresh model list fetch

## Debug Mode (if needed)

Edit `_kiropipe/kiropipe_config.yaml`:
```yaml
debug:
  debug_mode_enabled: true
  store_interaction_blocks: true
```

This will:
- Save the actual response to a file
- Show full request/response details
- Help diagnose format issues

## What Happens Next

### If Dynamic (model appears):
We'll implement full custom model injection:
```python
# Get models from config
custom_models = CONFIG.get_all_models()

# Inject into response
for model in custom_models:
    response_data['models'].append({
        'id': model['id'],
        'name': model['name'],
        'description': model.get('description', ''),
        'provider': model['provider'],
        'capabilities': ['chat', 'tools']
    })
```

### If Hardcoded (model doesn't appear):
We'll implement model replacement strategy:
```python
# Detect model selection in generateAssistantResponse
if 'generateAssistantResponse' in flow.request.path:
    body = json.loads(flow.request.text)
    selected_model = body.get('modelId')
    
    # Map to our custom model
    if selected_model in MODEL_MAPPING:
        custom_model = MODEL_MAPPING[selected_model]
        # Route to bridge with custom_model
```

## Current Injection Code

Location: `kiropipe.py` lines ~231 and ~497

**Request detection:**
```python
if 'ListAvailableModels' in flow.request.path:
    print("[INTERCEPTING MODEL LIST]")
```

**Response modification:**
```python
if 'ListAvailableModels' in flow.request.path:
    response_data = json.loads(flow.response.text)
    fake_model = {...}
    response_data['models'].append(fake_model)
    flow.response.content = json.dumps(response_data).encode()
```

## Files Modified
- `kiropipe.py` - Added injection code
- `_kiropipe/KIRO-PIPE_DEV_JOURNAL.md` - Updated Phase 12
- `_kiropipe/TEST_FAKE_MODEL.md` - This file
- `_kiropipe/devtools/capture_model_list.py` - NEW (for debugging)
