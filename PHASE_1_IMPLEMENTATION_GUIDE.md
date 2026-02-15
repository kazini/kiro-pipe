# Phase 1 Implementation Details & Debugging Guide

## Overview

Phase 1 consists of three Frida hooks that work together to:
1. **Disable** TLS certificate validation (so fake certificates from localhost are accepted)
2. **Log** all API requests and responses (so we can study the format)
3. **Redirect** traffic to localhost (so we can intercept it with our own server)

---

## How Each Hook Works

### Hook 1: Certificate Bypass

**File:** `certificate_bypass.js`

**Purpose:** Remove the barrier that prevents localhost connections

**Technical Details:**
- Node.js has a `rejectUnauthorized` setting that validates certificates
- By default: `rejectUnauthorized = true` (STRICT - rejects invalid certs)
- Our hook: sets `rejectUnauthorized = false` (PERMISSIVE - accepts all certs)

**How it works:**
```javascript
// Before hook: Kiro validates cert against trusted CAs
TLS_SOCKET.createSecureContext({
    rejectUnauthorized: true  // ← Only accept real certs
})

// After hook: Our modification
TLS_SOCKET.createSecureContext({
    rejectUnauthorized: false  // ← Accept ANY certificate (including fake)
})
```

**Why this matters:**
- Normally, connecting to `https://localhost:8888` would fail (no valid cert)
- With our hook, it succeeds (cert validation disabled)
- Allows us to impersonate `prod.us-east-1.auth.desktop.kiro.dev` from localhost

**Testing it worked:**
- Look for: `[TLS] SUCCESS - Certificate validation disabled`
- If Kiro makes requests without certificate errors → working

---

### Hook 2: Request Logger

**File:** `request_logger.js`

**Purpose:** Understand the Kiro API format by logging everything

**Technical Details:**
- Intercepts the `https.request()` function
- Logs method, hostname, path for every request
- Logs request headers (with auth token redacted)
- Logs response status code
- Logs response body (trimmed to first 200 chars)

**How it works:**
```javascript
// Original code (before interception)
const req = https.request('https://prod.us-east-1.auth.desktop.kiro.dev/auth', callback)
req.write(requestBody)
req.end()

// Through our hook
[HTTPS] request to: prod.us-east-1.auth.desktop.kiro.dev
[HTTPS] Request Body: {"username": "user@example.com", ...}
[HTTPS] Response: 200 OK
[HTTPS] Response Body: {"token": "abc123def456...", "expires": 3600}
```

**Sample output:**
```
[API-1] GET https://prod.us-east-1.auth.desktop.kiro.dev/user
[API-1] Headers: Authorization: Bearer token123, Content-Type: application/json
[API-1] Response: 200 OK
[API-1] Response Body: {"id": "user123", "name": "User Name", ...}
```

**Why we need this:**
- Understanding the exact request/response format is crucial for Phase 2
- We need to know what fields Kiro sends
- We need to know what fields Kiro expects back
- This guide us in building the translation layer

**Testing it worked:**
- Look for: `[API-*]` entries in console
- Should see request method, URL, headers
- Should see response status and body

---

### Hook 3: Request Redirect

**File:** `request_redirect.js`

**Purpose:** Route kiro.dev traffic to our local server

**Technical Details:**
- Intercepts TLS connection establishment
- When Kiro tries to connect to `prod.us-east-1.auth.desktop.kiro.dev`
- We redirect it to `localhost:8888`
- Also modifies DNS lookups to return `127.0.0.1`

**How it works:**

**Method 1 - TLS Connection Level:**
```javascript
// Original: Kiro tries to connect
tls.connect({
    host: 'prod.us-east-1.auth.desktop.kiro.dev',
    port: 443
})

// Through our hook
tls.connect({
    host: 'localhost',     // ← Changed!
    port: 8888,            // ← Changed!
    rejectUnauthorized: false  // ← Allow fake cert
})
```

**Method 2 - DNS Resolution Level:**
```javascript
// Original: Resolve domain name to IP
dns.lookup('prod.us-east-1.auth.desktop.kiro.dev')
// Returns: IP of real kiro.dev server

// Through our hook
dns.lookup('prod.us-east-1.auth.desktop.kiro.dev')
// Returns: 127.0.0.1 (localhost)
```

**Sample output:**
```
[TLS-CONNECT] prod.us-east-1.auth.desktop.kiro.dev:443 → localhost:8888
[DNS] prod.us-east-1.auth.desktop.kiro.dev → 127.0.0.1
```

**Why this matters:**
- Without redirection: requests still go to real server (no point)
- With redirection: we intercept the request BEFORE it leaves the machine
- Allows us to examine and modify the request
- Allows us to return a fake response

**Testing it worked:**
- Look for: `[TLS-CONNECT]` and `[DNS]` entries
- Should show redirection to localhost:8888
- Kiro should get connection refused/error (because server doesn't exist yet)

---

## Combined Hook Architecture

**File:** `combined.js`

Combines all three hooks into one script for convenience.

**Execution order:**
```
Process Start
    ↓
Frida Injects combined.js
    ↓
Part 1: Certificate Bypass Hook loads
    ↓
Part 2: Request Logger Hook loads
    ↓
Part 3: Request Redirect Hook loads
    ↓
Status Report printed
    ↓
Awaiting API Calls
```

**Performance impact:**
- Minimal - hooks only fire when APIs are called
- Logging adds ~5-10ms per request
- Redirection adds ~2-5ms per connection

---

## Debugging: What to Look For

### ✅ Success Indicators

```
[✓] Certificate Bypass Loaded
[✓] Request Logger Loaded
[✓] Request Redirection Loaded
✓ HOOKS ACTIVE AND MONITORING
```

If you see these, Phase 1 is working.

### ⚠️ Warning Signs

| Message | Meaning | Fix |
|---------|---------|-----|
| `[ERROR] Failed to attach` | Process not found or permission denied | Run as admin, check Kiro is running |
| `[WARNING] TLSSocket proxy failed` | Certificate hook partially failed | May still work - check if requests work |
| No `[API-*]` messages | Logger not catching requests | Kiro isn't making API calls, try using Chat feature |
| `[TLS] Can't connect to localhost` | Redirection working but no server | Expected! Phase 2 will fix this |

### 🔍 Detailed Debugging Steps

**Step 1: Verify Frida is installed correctly**
```bash
python -c "import frida; print(frida.__version__)"
# Should print version number like: 16.1.11
```

**Step 2: Verify Kiro process is running**
```bash
python attach.py --list | findstr Kiro
# Should find at least one Kiro process
```

**Step 3: Check hook loading individually**
```bash
# Test each hook separately
python attach.py --hook cert-only
# (use Kiro, check for [TLS] messages)

python attach.py --hook logger
# (use Kiro Chat, check for [API-*] messages)

python attach.py --hook redirect
# (use Kiro Chat, check for [REDIR-*] and [DNS] messages)
```

**Step 4: Examine actual API calls**
- Listen to logging output carefully
- Note the exact request format:
  - Method type (GET, POST, etc)
  - URL path
  - Request body fields
  - Response body fields
- This info is gold for Phase 2

---

## Common Issues & Solutions

### Issue 1: "Kiro crashes after attaching Frida"

**Cause:** One of the hooks has a bug causing a crash

**Solution:**
1. Try individual hooks to find which one crashes:
   ```bash
   python attach.py --hook cert-only      # Does Kiro work?
   python attach.py --hook logger         # Does Kiro work?
   python attach.py --hook redirect       # Does Kiro work?
   ```

2. If a specific hook crashes, that hook needs debugging
3. The other hooks in `combined.js` may need to be updated

### Issue 2: "I see requests being logged but then Kiro shows errors"

**This is NORMAL at Phase 1!**

Here's what's happening:
```
1. Kiro tries to connect to prod.us-east-1.auth.desktop.kiro.dev
2. Our redirect hook intercepts it
3. Redirects to localhost:8888
4. Connection refused (no server listening)
5. Kiro shows error
```

This is **expected**. In Phase 2, we'll create the translation server.

### Issue 3: "Hooks say they loaded but nothing is being logged"

**Cause:** Kiro isn't making API calls

**Solution:**
1. Make sure you're using features that trigger API calls:
   - Click "Chat" tab
   - Click "Ask AI" or similar button
   - Type a question
   - Press Enter

2. If still no output:
   - Wait a moment (sometimes there's a delay)
   - Try a different Kiro feature
   - Check if Kiro UI shows errors

3. If STILL no output:
   - The hooks loaded but aren't intercepting calls
   - This might mean Kiro uses a different network library
   - Try running different hooks individually to isolate

### Issue 4: "Module not found" or "require error"

**Cause:** Hook trying to require to a module that doesn't exist in Kiro's context

**Solution:**
1. This is a known issue with some Node.js versions
2. The individual hooks have try/catch to handle this
3. Not all hooks need to work - as long as ONE works, it's fine
4. Expected output from `combined.js`:
   ```
   [WARNING] TLSSocket proxy failed: ...
   [✓] Request Logger Loaded
   [✓] Request Redirection Loaded
   ```
   As long as you see some `[✓]` messages, you're good.

---

## How to Extract API Information from Logs

When you see requests like this:
```
[API-1] POST https://prod.us-east-1.auth.desktop.kiro.dev/completions
[API-1] Headers: content-type: application/json, custom-header: value
[API-1] Request Body: {"model":"gpt-4","messages":[{"role":"user","content":"hello"}],"temperature":0.7}
[API-1] Response: 200 OK
[API-1] Response Body: {"choices":[{"message":{"content":"response text"}}]}
```

**Extract and document:**

1. **Endpoint:** `/completions`
2. **Method:** `POST`
3. **Request Structure:**
   ```
   {
     "model": "gpt-4",
     "messages": [...],
     "temperature": 0.7
   }
   ```

4. **Response Structure:**
   ```
   {
     "choices": [
       {
         "message": {
           "content": "text"
         }
       }
     ]
   }
   ```

5. **Headers needed:**
   - `content-type: application/json`
   - Any authentication headers

This documentation becomes your API spec for Phase 2.

---

## Next: Phase 2 Preparation

While Phase 1 is running:

1. **Document every API call** you see
2. **Note the response format** for each endpoint
3. **Identify patterns** in request/response structure
4. **Research target LLM** format (OpenAI, Anthropic, etc)
5. **Design translation layer** that converts between them

Phase 2 will build a server on `localhost:8888` that:
- Receives requests from Kiro (redirected by Phase 1)
- Translates format (Kiro → Target LLM)
- Queries target LLM
- Translates response (Target LLM → Kiro)
- Returns response to Kiro

---

## Performance Considerations

**Hook overhead:**
- Certificate bypass: <1ms per connection
- Request logging: 5-10ms per request (for logging overhead)
- Request redirect: 2-5ms per connection

**Total impact:** Negligible for normal usage. Kiro should feel responsive.

**If Kiro is slow:**
- Try disabling request logger (`--hook redirect` only)
- Check if localhost:8888 server is causing timeouts
- Optimize translation server (Phase 2) for speed

---

## Advanced: Custom Modifications

**To add more endpoints to redirect:**
Edit `combined.js` (or individual hook files):
```javascript
const ENDPOINT_MAPPING = {
    'prod.us-east-1.auth.desktop.kiro.dev': REDIRECT_HOST,
    'app.kiro.dev': REDIRECT_HOST,
    'prod.download.desktop.kiro.dev': REDIRECT_HOST,
    'gamma.us-east-1.telemetry.desktop.kiro.dev': REDIRECT_HOST,
    // ADD YOUR ENDPOINTS HERE:
    'custom.kiro.dev': REDIRECT_HOST,
};
```

**To change redirect port:**
```javascript
const REDIRECT_PORT = 9000;  // Change from 8888
```

**To disable specific hooks in combined.js:**
Comment out the entire section:
```javascript
// ============================================================================
// PART 2: REQUEST LOGGING  ← COMMENT OUT ENTIRE SECTION TO DISABLE
// ============================================================================
/*
try {
    const https = require('https');
    // ... rest of logging code ...
}
*/
```

---

## Success Checklist

- [ ] Frida installed and working
- [ ] Kiro running
- [ ] Frida attachment successful
- [ ] All hooks loaded without errors
- [ ] Using Kiro Chat triggers API calls
- [ ] Can see request details in console
- [ ] Can see redirection to localhost
- [ ] Kiro shows error about connection (expected)
- [ ] Phase 1 documentation complete
- [ ] API request/response format documented for Phase 2

Once all items are checked, Phase 1 is complete and you're ready for Phase 2!
