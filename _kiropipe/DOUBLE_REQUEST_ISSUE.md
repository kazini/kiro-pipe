# Double Request Issue - Analysis & Fix

## The Problem

When using custom models (like Groq), Kiro sends **TWO requests** for every user message:

1. **Request #1:** `simple-task` model (6KB) → Goes to AWS Q
2. **Request #2:** `groq/llama-3.3-70b-versatile` (521KB) → Goes to Groq

**Result:** You pay for BOTH AWS Q credits AND Groq API tokens for every message!

---

## Root Cause

### How Kiro Works (Auto Mode)

Kiro's "auto" mode uses multiple models for different purposes:
- **simple-task**: Quick routing/planning decisions
- **auto**: Full context processing
- **complex-task**: Heavy reasoning tasks

When you select a custom model, Kiro still tries to use its internal models for routing.

### The Routing Logic

```python
# In kiropipe.py request() method:

if 'generateAssistantResponse' in flow.request.path:
    selected_model = parse_model_from_request()
    model_info = CONFIG.get_model_info(selected_model)
    
    if model_info and model_info['provider'] != 'kiro':
        # Intercept and route to custom provider
        route_to_custom_provider()
        return  # ← Stops here, doesn't reach AWS
    
    # If model_info is None (unknown model):
    # Falls through → Request continues to AWS Q!
```

### What Happens

**Scenario 1: simple-task request**
- `model_info = None` (not in your config)
- Condition `if model_info and ...` → FALSE
- **Falls through** → AWS Q processes it
- **Cost:** AWS Q credits consumed

**Scenario 2: groq/llama-3.3-70b-versatile request**
- `model_info` exists (in your config)
- Condition `if model_info and ...` → TRUE
- **Intercepted** → Routed to Groq
- **Cost:** Groq API tokens consumed

**Total Cost:** BOTH AWS Q + Groq for every message!

---

## The Fix ✅

Added logic to **block unknown models** when Kiro models are disabled:

```python
# Step 4: Block unknown models if Kiro models are disabled
if not ALLOW_KIRO_MODELS and not model_info:
    if DEBUG_MODE_ENABLED:
        print(f"[BLOCKED UNKNOWN MODEL] Model '{selected_model}' not in config")
    
    # Return warning message to user
    warning_msg = f"⚠️ Model '{selected_model}' is not configured."
    return_warning_response()
    return  # ← Blocks the request
```

### What This Does

1. If `kiro_endpoint.models: false` (Kiro models disabled)
2. AND model is not in your config (like "simple-task")
3. → **Block the request** with a warning message
4. → **No AWS Q credits consumed**

---

## Configuration

In `_kiropipe/kiropipe_config.yaml`:

```yaml
kiro_endpoint:
  models: false  # ← Set to false to block Kiro's internal models
```

**When set to `false`:**
- ✅ Only your configured custom models work
- ✅ Unknown models (simple-task, auto, etc.) are blocked
- ✅ No double billing
- ❌ Kiro's auto mode won't work (but you're using custom models anyway)

**When set to `true`:**
- ✅ Kiro's internal models work (simple-task, auto, etc.)
- ✅ Your custom models also work
- ⚠️ **Double requests possible** if Kiro uses internal models for routing
- ⚠️ **Double billing** (AWS Q + custom provider)

---

## Recommendations

### Option 1: Block Kiro Models (Recommended)
```yaml
kiro_endpoint:
  models: false
```

**Pros:**
- No double billing
- Only pay for your custom models
- Clear cost tracking

**Cons:**
- Kiro's auto mode won't work
- Must manually select your custom model

### Option 2: Allow Both (Not Recommended)
```yaml
kiro_endpoint:
  models: true
```

**Pros:**
- Kiro's auto mode works
- Can use both Kiro and custom models

**Cons:**
- **Double billing risk**
- Harder to track costs
- Wasteful if you only want custom models

### Option 3: Hybrid Approach
Keep Kiro models enabled but monitor usage:

```yaml
kiro_endpoint:
  models: true

debug:
  debug_mode_enabled: true  # Monitor which models are used
```

Watch logs for:
```
[MODEL SELECTED] simple-task (Custom)  ← Kiro's internal model
[MODEL SELECTED] groq/llama-3.3-70b-versatile (Custom)  ← Your model
```

If you see both, you're being double-billed.

---

## Testing

### Test 1: Verify Blocking Works
1. Set `kiro_endpoint.models: false`
2. Restart kiropipe
3. Send a message
4. Check logs for:
   ```
   [BLOCKED UNKNOWN MODEL] Model 'simple-task' not in config
   ```

### Test 2: Check for Double Requests
1. Enable debug mode
2. Send a message
3. Count how many `[MODEL SELECTED]` lines appear
4. Should only see ONE (your custom model)

### Test 3: Verify No AWS Q Usage
1. Check AWS Q billing/usage dashboard
2. Should show zero usage when using custom models

---

## Why This Happens

Kiro's architecture assumes you're using AWS Q models. When you introduce custom models:

1. Kiro still tries to use its internal routing logic
2. Sends "simple-task" request for quick decisions
3. Then sends your actual model request
4. Both go through the proxy
5. One goes to AWS Q, one goes to your provider
6. **You pay twice**

This is a limitation of intercepting at the proxy level - we can't prevent Kiro from making the first request, we can only block it.

---

## Alternative Solutions (Not Implemented)

### 1. Request Deduplication
Track requests and drop duplicates within a time window.

**Pros:** Automatic
**Cons:** Complex, might drop legitimate requests

### 2. Model Aliasing
Map "simple-task" → your custom model in config.

**Pros:** Transparent to Kiro
**Cons:** Might break Kiro's routing logic

### 3. Selective Blocking
Only block specific Kiro models (simple-task, auto) but allow others.

**Pros:** More granular control
**Cons:** More configuration complexity

---

## Summary

- ✅ **Fix Applied:** Unknown models are now blocked when `kiro_endpoint.models: false`
- ✅ **No More Double Billing:** Only your custom models are used
- ⚠️ **Trade-off:** Kiro's auto mode won't work (but you're using custom models anyway)
- 📊 **Monitor:** Enable debug mode to verify only one request per message

**Recommended Setting:**
```yaml
kiro_endpoint:
  models: false  # Block Kiro models, use only custom
```
