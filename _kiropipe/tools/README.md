# Frida Interception Scripts for Kiro

Phase 1 implementation: Runtime injection hooks for certificate bypass, request logging, and traffic redirection.

## Files

### Core Scripts
- **attach.py** - Main Python attachment script (runs Frida and injects hooks)
- **combined.js** - All three hooks combined (recommended for production use)
- **certificate_bypass.js** - Certificate validation bypass (standalone)
- **request_logger.js** - HTTPS request logging (standalone)
- **request_redirect.js** - Request redirection to localhost (standalone)

## Installation

### Prerequisites
```bash
pip install frida frida-tools
```

### Verify Frida Installation
```bash
frida --version
frida-ps   # List running processes
```

## Quick Start

### 1. Start Kiro Application
Launch Kiro normally through your installed shortcut or:
```bash
C:\Users\Kazini\Vault\Programas\Coding\my_programming_stuff\AI\projects\open-cli_project\kiro-conduit\Kiro\Kiro.exe
```

### 2. List Running Processes
```bash
python attach.py --list
```

Look for **Kiro** or **Kiro.exe** in the list.

### 3. Attach Frida and Inject Hooks
```bash
# All hooks combined (recommended)
python attach.py --hook combined

# OR individual hooks
python attach.py --hook cert-only      # Only certificate bypass
python attach.py --hook logger         # Only request logging
python attach.py --hook redirect       # Only request redirection
```

### 4. Monitor Output
The script will display:
- ✓ Successful attachment confirmation
- 🔐 Certificate validation bypass status
- 📡 HTTPS request details (method, URL, headers)
- 🔄 Request redirections to localhost:8888
- 📊 Response details

Press **Ctrl+C** to stop monitoring.

## Hook Behaviors

### Certificate Bypass Hook
**What it does:**
- Disables TLS certificate validation in Node.js
- Allows Kiro to make requests without certificate errors
- Removes the barrier to localhost impersonation

**How to verify it's working:**
- Look for `[TLS] SUCCESS - Certificate validation disabled` in output
- Kiro should make connections without certificate errors

### Request Logger Hook
**What it does:**
- Intercepts all HTTPS requests to kiro.dev domains
- Logs method, hostname, path
- Logs request headers (with auth redacted)
- Logs response status and body

**Output example:**
```
[API-1] GET https://prod.us-east-1.auth.desktop.kiro.dev/authenticate
[API-1] Headers: content-type: application/json, authorization: ***REDACTED***
[API-1] Response: 200 OK
[API-1] Response Body: {"token": "...", "expires": ...}
```

### Request Redirect Hook
**What it does:**
- Intercepts TLS connections to kiro.dev endpoints
- Redirects hostname to localhost:8888
- Preserves request method, path, and headers
- Adds proxy headers (X-Original-Host, X-Forwarded-Proto)

**Redirected endpoints:**
- `prod.us-east-1.auth.desktop.kiro.dev` → `localhost:8888`
- `app.kiro.dev` → `localhost:8888`
- `prod.download.desktop.kiro.dev` → `localhost:8888`
- `gamma.us-east-1.telemetry.desktop.kiro.dev` → `localhost:8888`

**Output example:**
```
[REDIR-1] prod.us-east-1.auth.desktop.kiro.dev:443 → localhost:8888
[DNS] prod.us-east-1.auth.desktop.kiro.dev → 127.0.0.1
```

## Next Steps: Translation Server

Once you have Frida interception working, you need a local server on `localhost:8888` that:

1. **Accepts requests** from Kiro
2. **Translates request format** from Kiro → OpenAI/Anthropic API
3. **Queries alternative LLM** (OpenAI, Claude, local llama.cpp, etc.)
4. **Translates response** back to Kiro format
5. **Returns response** with fake certificate (Kiro accepts because validation is disabled)

### Translation Server Setup
```bash
# Create translation server directory
mkdir translation-server
cd translation-server

# Create virtual environment (optional but recommended)
python -m venv venv
./venv/Scripts/activate

# Create main server file
# (See next section for implementation)
```

### Minimal Translation Server Example
```python
# minimal_server.py
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/authenticate', methods=['POST'])
def authenticate():
    """Fake authentication endpoint that Kiro calls"""
    data = request.json
    
    # Return fake token
    return jsonify({
        'token': 'fake-kiro-token-12345',
        'expires_in': 3600,
        'user_id': 'local-user'
    })

@app.route('/api/completions', methods=['POST'])
def completions():
    """Translate Kiro completion request to OpenAI and back"""
    kiro_request = request.json
    
    # TODO: Translate kiro_request to OpenAI format
    # TODO: Query OpenAI API
    # TODO: Translate response back to Kiro format
    
    return jsonify({
        'choices': [{
            'message': {
                'content': 'Response from alternative LLM'
            }
        }]
    })

if __name__ == '__main__':
    app.run(host='localhost', port=8888, ssl_context='adhoc')
```

## Troubleshooting

### "Cannot find process: Kiro"
- Make sure Kiro is running
- Use `python attach.py --list` to verify process name
- Try full path: `python attach.py --process Kiro.exe`

### "Failed to attach: Permission Denied"
- Run Python script as Administrator
- Or run Kiro without admin privileges

### "Hooks loaded but no requests appearing"
- Kiro might be using different API endpoints
- Check that you're actually using Kiro features that make API calls
- Try clicking "Chat" or "Generate" to trigger requests

### "TLS/Certificate errors in output"
- This is expected - the bypass hook is doing its job
- These would normally be fatal errors
- The bypass allows them to proceed

### "Requests going to real server instead of localhost"
- DNS hook might not be intercepting
- Try using the TLS redirect hook instead (included in combined.js)
- If using standalone logger with redirect, make sure redirect hook is active

## Advanced Usage

### Custom Endpoint Mapping
Edit `combined.js` or `request_redirect.js`:
```javascript
const ENDPOINT_MAPPING = {
    'prod.us-east-1.auth.desktop.kiro.dev': REDIRECT_HOST,
    'your-custom-endpoint.kiro.dev': REDIRECT_HOST,  // Add custom
    // ...
};
```

### Different Redirect Port
Edit `combined.js` or `request_redirect.js`:
```javascript
const REDIRECT_PORT = 9999;  // Change from 8888 to 9999
```

### Modify Log Verbosity
Edit `combined.js`:
```javascript
// For less output, comment out console.log statements
// For more output, add additional logging

if (socketCount % 100 === 0) {
    console.log(...);  // Only log every 100th connection
}

// Change to:
console.log(...);  // Log every connection
```

## Architecture

```
User's Computer
├── Kiro.exe (Running Application)
├── Frida Agent (Injected by attach.py)
│   ├── Certificate Bypass Hook
│   ├── Request Logger Hook
│   └── Request Redirect Hook
└── Translation Server (localhost:8888)
    ├── Request Receiver
    ├── Format Translator
    ├── LLM Query Handler
    └── Response Translator
```

## Success Indicators

✅ **Frida Injection Successful:**
- `[✓] Hooks injected successfully` appears
- No "Failed to inject" errors

✅ **Certificate Bypass Working:**
- `[✓] Certificate Bypass Loaded` appears
- Kiro makes requests without certificate errors

✅ **Request Logging Working:**
- `[API-1] GET https://prod.us-east-1.auth.desktop.kiro.dev/...` appears
- You can see request details and response bodies

✅ **Request Redirection Working:**
- `[REDIR-1] ... → localhost:8888` appears
- DNS shows `→ 127.0.0.1`
- Check netstat shows connection to localhost:8888

## Security Notes

⚠️ **Important:**
- This is for local development and research only
- Disabling certificate validation makes MITM attacks possible
- The injected code runs with full process permissions
- Never use this on untrusted networks
- Keep your translation server secure (localhost only)

## Next Phase

Once Frida interception is confirmed working:

1. Analyze the actual Kiro API request/response format
2. Build translation server that converts between:
   - Kiro format ↔ OpenAI format
   - Kiro format ↔ Anthropic Claude format
   - Kiro format ↔ Custom local LLM format
3. Query alternative LLM backends
4. Return translated responses

Estimated Phase 2 development time: 1 week

---

## Support

If Frida hooks aren't working:
1. Check Frida installation: `frida --version`
2. Verify process: `frida-ps` and look for Kiro
3. Try running as Administrator
4. Check that Kiro is actually making API calls (use features that require LLM)
5. Review console output for specific error messages
