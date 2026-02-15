# Model List Testing Plan

## Objective
Determine whether Kiro uses a hardcoded or dynamic model list to decide our implementation strategy.

## The Question
**Does Kiro fetch its model list from an API, or is it hardcoded?**

This determines whether we can:
- **Add custom models** to the list (if dynamic)
- **Replace existing models** when selected (if hardcoded)

## Testing Approach

### Phase 1: Endpoint Discovery (CURRENT)

**What we're doing:**
- Modified `kiropipe.py` to automatically detect model-related API calls
- Added keyword monitoring for: `model`, `list`, `available`, `configuration`, `select`, `choice`
- These will be logged in MAGENTA even with debug mode off

**How to test:**
1. Run `python kiropipe.py`
2. Open Kiro
3. Look for model selection UI (dropdown, settings, etc.)
4. Try to switch models
5. Watch console for MAGENTA alerts about model-related endpoints

**Expected outcomes:**
- **If we see model endpoints**: Kiro fetches models dynamically → Proceed to Phase 2
- **If we see nothing**: Models are hardcoded → Proceed to Phase 3

### Phase 2: Injection Testing (if dynamic models found)

**What we'll do:**
- Use `test_model_injection.py` to generate fake model list responses
- Intercept the model endpoint we discovered
- Inject fake models: "Custom Test Model 1", "Custom Test Model 2"
- Observe if they appear in Kiro's UI

**Tools ready:**
- `_kiropipe/devtools/test_model_injection.py` - Generates test responses
- `_kiropipe/devtools/discover_endpoints.py` - Analyzes captured traffic

**Implementation:**
```python
# In kiropipe.py, add:
if 'getAvailableModels' in flow.request.path:  # Use actual endpoint found
    # Load fake model list
    fake_response = create_fake_model_list()
    flow.response = http.Response.make(
        200,
        fake_response,
        {"Content-Type": "application/vnd.amazon.eventstream"}
    )
    return
```

**Success criteria:**
- Fake models appear in Kiro's model selection UI
- We can select them (even if they don't work yet)

### Phase 3: Model Replacement Strategy (if hardcoded)

**What we'll do:**
- Accept that we can't add new models to the list
- Instead, intercept when user selects a model
- Transparently route to our custom backend

**Implementation:**
```python
# Detect model selection from request body
if 'generateAssistantResponse' in flow.request.path:
    body = json.loads(flow.request.text)
    selected_model = body.get('modelId') or body.get('model')
    
    # Map Kiro models to our custom models
    model_mapping = {
        'claude-3-5-sonnet': 'our-custom-model',
        'claude-3-opus': 'our-other-model'
    }
    
    if selected_model in model_mapping:
        # Route to our custom backend
        custom_model = model_mapping[selected_model]
        # ... forward to bridge with custom_model
```

## Usage Limits Toggle Strategy

**Problem:** Usage limits should only apply when using Kiro's models, not custom ones.

**Current behavior:**
- Static toggle (always on/off/auto)
- Doesn't adapt to model selection

**Desired behavior:**
- Kiro model selected → Allow usage limits (AWS tracks usage)
- Custom model selected → Block usage limits (we're not using AWS)

**Implementation:**
```python
class KiroInterceptor:
    def __init__(self):
        self.current_model = CURRENT_MODEL
        self.model_is_kiro = True  # Track if using Kiro's backend
    
    def request(self, flow):
        # Detect model from request
        if 'generateAssistantResponse' in flow.request.path:
            body = json.loads(flow.request.text)
            model = body.get('modelId') or body.get('model')
            
            # Update tracking
            self.current_model = model
            self.model_is_kiro = (model == 'kiro-default' or model in KIRO_MODELS)
        
        # Dynamic usage limits blocking
        if 'getUsageLimits' in flow.request.path:
            if not self.model_is_kiro:
                # Block usage limits for custom models
                flow.response = http.Response.make(
                    200,
                    b'{"limits":[],"subscriptionInfo":{"type":"FREE"}}',
                    {"Content-Type": "application/json"}
                )
                return
```

## Current Status

✅ **Completed:**
- Model-related endpoint detection added to `kiropipe.py`
- Test tools created (`test_model_injection.py`, `discover_endpoints.py`)
- Development journal updated (Phase 12)
- Testing plan documented

⏳ **Awaiting:**
- Endpoint discovery results from live testing
- Decision on hardcoded vs dynamic models
- Implementation of chosen strategy

## Next Steps

1. **Run kiropipe.py and use Kiro**
   - Look for model selection UI
   - Try to switch models
   - Watch for MAGENTA alerts in console

2. **If model endpoint found:**
   - Run `python _kiropipe/devtools/test_model_injection.py`
   - Modify kiropipe.py to inject fake models
   - Test if they appear in UI

3. **If no model endpoint found:**
   - Implement model replacement strategy
   - Map Kiro models to custom backends
   - Test transparent routing

4. **Implement dynamic usage limits:**
   - Track current model type
   - Toggle usage limits based on model
   - Test with both Kiro and custom models

## Files Modified

- `kiropipe.py` - Added model endpoint detection
- `_kiropipe/KIRO-PIPE_DEV_JOURNAL.md` - Added Phase 12
- `_kiropipe/devtools/test_model_injection.py` - NEW
- `_kiropipe/devtools/discover_endpoints.py` - NEW
- `_kiropipe/MODEL_TESTING_PLAN.md` - NEW (this file)

## Questions to Answer

1. Does Kiro fetch models via API?
2. If yes, what endpoint and format?
3. If no, how are models stored (binary, config file)?
4. Can we inject fake models successfully?
5. How does Kiro identify which model is selected?
6. Where in the request is the model ID sent?

## Success Metrics

**For Dynamic Models:**
- ✓ Fake models appear in Kiro UI
- ✓ Can select custom models
- ✓ Custom models route to our backends
- ✓ Usage limits toggle correctly

**For Hardcoded Models:**
- ✓ Model selection detected in requests
- ✓ Transparent routing to custom backends
- ✓ User sees Kiro models, gets custom responses
- ✓ Usage limits toggle correctly
