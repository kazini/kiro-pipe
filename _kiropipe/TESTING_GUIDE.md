# Testing Guide - Model Injection System

## Prerequisites
1. Enable debug mode in `kiropipe.py`: `DEBUG_MODE_ENABLED = True`
2. Ensure `_kiropipe/devtools/dummy_models.json` exists with test models

## Test Scenarios

### Test 1: Verify Model Injection Works
**Goal**: Confirm that dummy models are injected into Kiro's model list

**Steps**:
1. Run `python kiropipe.py`
2. Wait for Kiro to launch
3. Look for console output showing model injection

**Expected Output**:
```
============================================================
[INJECTING CUSTOM MODELS]
============================================================
Original Kiro models: 7
Tracked Kiro model IDs: 7
Loaded 3 dummy test model(s)
[OVERRIDE] Replaced Kiro model: auto (inherits Kiro type)
Injected 3 custom model(s):
  - Test Dummy 1
  - Test Subject Beta (2)
  - Auto (OVERRIDDEN) (override)
Total models: 9
============================================================
```

**Verification**:
- Open Kiro's model selector
- You should see "Test Dummy 1", "Test Subject Beta (2)", and "Auto (OVERRIDDEN)"

---

### Test 2: Verify Usage Limits Blocking for Custom Models
**Goal**: Confirm that usage limits are blocked when custom models exist

**Steps**:
1. Run `python kiropipe.py` with debug mode enabled
2. Wait for Kiro to launch
3. Look for usage limits check in console

**Expected Output**:
```
[USAGE LIMITS CHECK]
  Custom model IDs: {'test-dummy-1', 'test-dummy-2'}
  Count: 2
  Should block: True
 [BLOCKED USAGE LIMITS] https://q.us-east-1.amazonaws.com/getUsageLimits?...
  Reason: Custom models available (2 models)
```

**Verification**:
- Usage limits should be blocked (fake FREE response sent)
- Custom models should be available in the model list

---

### Test 3: Verify Dummy Model Override Feature
**Goal**: Confirm that dummy models can override existing Kiro models and inherit their type

**Steps**:
1. Check `_kiropipe/devtools/dummy_models.json` has a model with `modelId: "auto"`
2. Run `python kiropipe.py` with debug mode enabled
3. Look for override message in console

**Expected Output**:
```
[OVERRIDE] Replaced Kiro model: auto (inherits Kiro type)
```

**Verification**:
- The "Auto" model should now show as "Auto (OVERRIDDEN)" in Kiro
- The model should have `rateMultiplier: 999.0` (from dummy_models.json)
- When you select this model, usage limits should NOT be blocked (because it inherits Kiro type)

**Important**: The overridden model is NOT added to `custom_model_ids` because it inherits Kiro type.

---

### Test 4: Verify Model Selection Detection
**Goal**: Confirm that model selection is detected and tracked

**Steps**:
1. Run `python kiropipe.py` with debug mode enabled
2. In Kiro, select "Test Dummy 1" from the model list
3. Send a message to trigger `generateAssistantResponse`
4. Look for model selection message in console

**Expected Output**:
```
[MODEL SELECTED] test-dummy-1 (Custom)
```

**Verification**:
- Model selection should be logged
- Model type (Kiro vs Custom) should be correct

---

### Test 5: Verify Override Doesn't Block Usage Limits
**Goal**: Confirm that overridden Kiro models don't trigger usage limits blocking

**Steps**:
1. Ensure dummy_models.json has a model with `modelId: "auto"` (overrides Kiro's Auto)
2. Run `python kiropipe.py` with debug mode enabled
3. Select the overridden "Auto (OVERRIDDEN)" model
4. Check usage limits behavior

**Expected Behavior**:
- Usage limits check shows: `Should block: True` (because test-dummy-1 and test-dummy-2 exist)
- But the overridden "auto" model is NOT in `custom_model_ids`
- This is correct: usage limits are blocked based on ANY custom models existing, not the selected model

**Note**: Usage limits blocking happens BEFORE model selection, so it checks if ANY custom models exist, not which model is currently selected.

---

## Troubleshooting

### Issue: Dummy models not appearing
**Solution**: 
- Check `_kiropipe/devtools/dummy_models.json` exists
- Verify JSON is valid
- Enable debug mode to see error messages

### Issue: Usage limits not blocked
**Solution**:
- Check `self.custom_model_ids` in debug output
- Verify custom models are being added to the set
- Check if usage limits check happens before model injection

### Issue: Override not working
**Solution**:
- Verify the dummy model has the exact same `modelId` as the Kiro model
- Check debug output for `[OVERRIDE]` message
- Ensure the model exists in Kiro's original list

---

## Debug Output Reference

### Model Injection
```
[INJECTING CUSTOM MODELS]
Original Kiro models: X
Tracked Kiro model IDs: X
Loaded X dummy test model(s)
[OVERRIDE] Replaced Kiro model: modelId (inherits Kiro type)
Injected X custom model(s):
  - Model Name 1
  - Model Name 2
Total models: X
```

### Usage Limits Check
```
[USAGE LIMITS CHECK]
  Custom model IDs: {'model-1', 'model-2'}
  Count: X
  Should block: True/False
 [BLOCKED USAGE LIMITS] URL
  Reason: Custom models available (X models)
```

### Model Selection
```
[MODEL SELECTED] model-id (Kiro/Custom)
```

### Override
```
[OVERRIDE] Replaced Kiro model: modelId (inherits Kiro type)
[OVERRIDE] Replaced custom model: modelId
```
