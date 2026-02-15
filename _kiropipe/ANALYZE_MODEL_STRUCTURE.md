# Analyze Model Structure

## What We're Doing
Extracting the EXACT model structure that Kiro uses so we can match it perfectly.

## Steps

### 1. Restart KiroPipe
```bash
python kiropipe.py
```

### 2. Wait for Model List Request
Kiro will automatically fetch the model list. Watch for:
```
============================================================
 [ANALYZING MODEL LIST]
============================================================
✓ Saved original response to: _kiropipe/debug_logs/original_models.json
```

### 3. Check the Saved Files

**Original response:**
```
_kiropipe/debug_logs/original_models.json
```
Complete response from AWS

**Models array:**
```
_kiropipe/debug_logs/models_array.json
```
Just the array of models for easy viewing

**Modified response:**
```
_kiropipe/debug_logs/modified_models.json
```
Response with our fake model injected

### 4. Analyze the Structure

Open `models_array.json` and look at the fields:
- What keys does each model have?
- Are there required fields we're missing?
- Are there validation fields (checksums, signatures)?
- Is there a specific order or format?

### 5. Compare Original vs Modified

Compare the files to see:
- Did our fake model match the structure?
- Are there any differences?
- Did we miss any required fields?

## What to Look For

### Common Model Fields
- `id` - Model identifier
- `name` or `displayName` - Display name
- `description` - Model description
- `provider` - Provider name
- `capabilities` - Array of capabilities
- `status` - Availability status
- `version` - Model version
- `arn` - AWS ARN (might be required!)
- `createdAt` - Timestamp
- `updatedAt` - Timestamp

### Validation Fields
- `signature` - Cryptographic signature
- `checksum` - Data integrity check
- `verified` - Verification status

If these exist, Kiro might be validating the model list!

## Possible Issues

### Issue 1: Missing Required Fields
**Symptom:** Model doesn't appear
**Solution:** Add all fields from real models

### Issue 2: Validation/Signature
**Symptom:** Model doesn't appear, no errors
**Solution:** Kiro might be validating signatures - we'd need to bypass this

### Issue 3: ARN Required
**Symptom:** Model doesn't appear
**Solution:** Generate a fake but valid-looking ARN

### Issue 4: Whitelist Check
**Symptom:** Model doesn't appear
**Solution:** Kiro might check model IDs against a whitelist - we'd need model replacement strategy

## Next Steps

After analyzing the structure:

### If structure matches and model still doesn't appear:
1. Check for validation fields
2. Check browser console for errors
3. Try different model IDs
4. Consider model replacement strategy

### If structure doesn't match:
1. Update fake model to match exactly
2. Test again
3. Iterate until it works

## Files to Check
- `_kiropipe/debug_logs/original_models.json` - Original response
- `_kiropipe/debug_logs/models_array.json` - Just the models
- `_kiropipe/debug_logs/modified_models.json` - With fake model

## Console Output
The console will show:
- Response structure (keys)
- Model count
- Example model fields
- Whether injection succeeded
