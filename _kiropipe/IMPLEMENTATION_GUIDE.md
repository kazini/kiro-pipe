# Model Injection Implementation Guide

## Overview
This guide explains how to implement the complete model injection system with:
- Dynamic model list fetching from Kiro
- Tracking Kiro vs custom models
- Injecting config models + dummy test models
- Routing based on model type
- Dynamic usage limits toggle

## Changes Required

### 1. Update KiroInterceptor.__init__ (Line ~220)

**Current:**
```python
class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to_file = DEBUG_STORE_INTERACTION_BLOCKS
        self.telemetry_blocked = 0
        self.current_model = CURRENT_MODEL
```

**New:**
```python
class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to_file = DEBUG_STORE_INTERACTION_BLOCKS
        self.telemetry_blocked = 0
        self.current_model = CURRENT_MODEL
        self.kiro_model_ids = set()  # Track Kiro's original model IDs
        self.custom_model_ids = set()  # Track our custom model IDs
        self.model_is_kiro = True  # Track if current model is Kiro's
```

### 2. Remove Test Interception Message (Line ~231)

**Remove this block:**
```python
# EXPERIMENTAL: Inject fake model into ListAvailableModels response
if 'ListAvailableModels' in flow.request.path:
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Style.BRIGHT} [INTERCEPTING MODEL LIST]{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Testing if Kiro accepts custom models...{Style.RESET_ALL}")
    
    # Let the request go through first to get the real response
    # We'll modify it in the response() method
    pass
```

### 3. Add Model Selection Detection in request() method

**Add after the injection queue check (around line ~400):**

```python
# Detect model selection in generateAssistantResponse requests
if 'generateAssistantResponse' in flow.request.path:
    try:
        body = json.loads(flow.request.text)
        selected_model = body.get('modelId') or body.get('model')
        
        if selected_model:
            self.current_model = selected_model
            self.model_is_kiro = selected_model in self.kiro_model_ids
            
            if DEBUG_MODE_ENABLED:
                model_type = "Kiro" if self.model_is_kiro else "Custom"
                print(f"{Fore.CYAN}[MODEL SELECTED] {selected_model} ({model_type}){Style.RESET_ALL}")
    except:
        pass
```

### 4. Update Usage Limits Check (Line ~255)

**Current:**
```python
# Dynamic usage limits blocking
should_block_limits = CONFIG.should_block_usage_limits(self.current_model)
if should_block_limits and 'getUsageLimits' in flow.request.path:
```

**New:**
```python
# Dynamic usage limits blocking (block for custom models only)
if 'getUsageLimits' in flow.request.path and not self.model_is_kiro:
```

### 5. Replace response() method (Line ~497)

**Replace the entire response() method with the implementation from:**
`_kiropipe/new_response_method.py`

Key features:
- Tracks Kiro's original model IDs
- Injects models from config
- Injects dummy test models (debug mode only)
- All debug messages wrapped in `if DEBUG_MODE_ENABLED:`
- Graceful error handling for dummy_models.json

### 6. Update Model-Related Endpoint Detection (Line ~419)

**Make it debug-only:**

**Current:**
```python
if is_model_related:
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Style.BRIGHT} [MODEL-RELATED ENDPOINT DETECTED]{Style.RESET_ALL}")
    ...
```

**New:**
```python
if is_model_related and DEBUG_MODE_ENABLED:
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Style.BRIGHT} [MODEL-RELATED ENDPOINT DETECTED]{Style.RESET_ALL}")
    ...
```

## Files to Create

### 1. dummy_models.json (Already created)
Location: `_kiropipe/devtools/dummy_models.json`

Contains test models for debugging. Only loaded when DEBUG_MODE_ENABLED = True.

## Testing

### 1. Test with Config Models

Edit `_kiropipe/kiropipe_config.yaml`:
```yaml
providers:
  anthropic:
    enabled: true
    api_key: "your-key"
    models:
      - name: "claude-3-5-sonnet-20241022"
        alias: ["claude"]
        description: "Claude 3.5 Sonnet"

default_model: "claude"
```

Run kiropipe.py and check if "claude" appears in Kiro's model selector.

### 2. Test with Dummy Models

Enable debug mode:
```yaml
debug:
  debug_mode_enabled: true
```

Run kiropipe.py and check if "🧪 Test Dummy 1" and "🧪 Test Dummy 2" appear.

### 3. Test Model Selection

1. Select a custom model in Kiro
2. Send a message
3. Check console for: `[MODEL SELECTED] claude-3-5-sonnet-20241022 (Custom)`
4. Verify it routes to bridge server

### 4. Test Usage Limits Toggle

1. Select Kiro model → Usage limits should be allowed
2. Select custom model → Usage limits should be blocked
3. Check console for blocking messages (debug mode)

## Expected Console Output

### With Debug Mode OFF:
- No model injection messages
- No model selection messages
- No AWS request/response details
- Clean, minimal output

### With Debug Mode ON:
```
============================================================
 [INJECTING CUSTOM MODELS]
============================================================
Original Kiro models: 7
Tracked Kiro model IDs: 7
Injected 3 custom model(s):
  - claude
  - llama
  - 🧪 Test Dummy 1
Total models: 10
============================================================

[MODEL SELECTED] claude-3-5-sonnet-20241022 (Custom)

[BLOCKED USAGE LIMITS] https://q.us-east-1.amazonaws.com/getUsageLimits
```

## Integration with Existing Features

### Model Routing (Already exists)
The existing code in `request()` method around line ~301 handles routing:
```python
if 'generateAssistantResponse' in flow.request.path:
    model_info = CONFIG.get_model_info(self.current_model)
    
    if model_info and model_info['provider'] != 'kiro':
        # Forward to custom provider
        ...
```

This will automatically work with the new model selection detection.

### Bridge Server (Already exists)
The bridge server code around line ~310 will receive the custom model requests.

### Config System (Already exists)
The config loader already has methods to get models:
- `CONFIG.get_enabled_providers()`
- `CONFIG.get_provider_config(provider_name)`
- `CONFIG.get_model_info(model_id)`

## Summary of Changes

1. ✅ Track Kiro vs custom model IDs
2. ✅ Inject config models into list
3. ✅ Inject dummy test models (debug only)
4. ✅ Detect model selection
5. ✅ Toggle usage limits dynamically
6. ✅ All debug messages conditional
7. ✅ Graceful error handling
8. ✅ Integration with existing routing

## Files Modified
- `kiropipe.py` - Main implementation
- `_kiropipe/devtools/dummy_models.json` - Test models (NEW)
- `_kiropipe/new_response_method.py` - Reference implementation (NEW)
- `_kiropipe/IMPLEMENTATION_GUIDE.md` - This file (NEW)
