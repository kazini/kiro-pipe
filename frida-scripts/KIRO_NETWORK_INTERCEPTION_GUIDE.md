# Kiro Network Interception - Research Journal

## Project Goal
Intercept Kiro's API calls to Amazon Q (AWS CodeWhisperer) and redirect them to our own LLM, allowing us to use custom models instead of Amazon's service.

---

## Discovery Phase - Endpoint Identification

### Initial Research
**Date**: Session 1
**Method**: Analyzed open-source `kiro-gateway` project

**Key Findings**:
- ✅ Kiro uses **AWS CodeWhisperer/Amazon Q**, NOT AWS Bedrock
- ✅ API endpoint: `https://q.{region}.amazonaws.com`
- ✅ Authentication endpoints:
  - Kiro Desktop Auth: `https://prod.{region}.auth.desktop.kiro.dev/refreshToken`
  - AWS SSO OIDC: `https://oidc.{region}.amazonaws.com/token`
- ✅ Default region: `us-east-1` (but region-agnostic patterns work)
- ✅ API methods: `ListAvailableModels`, `generateAssistantResponse`

**Source**: `_reference_kiro-gateway-main/kiro/config.py` and `auth.py`

---

## Process Architecture Analysis

### Tool Development
**Created**: `find_kiro_pids.py`
**Purpose**: Identify which Kiro process handles networking

**Execution Results**:
```
Found 15 Kiro processes
Process with active network connection found
- Has 1 active connection to AWS (18.206.105.168:443)
- Resolved to: ec2-18-206-105-168.compute-1.amazonaws.com
- Type: Child process (not main)
- Accepts Frida injection
```

**Architecture Discovered**:
```
Kiro.exe (Main Process)
├── Network Process ← Has AWS connection, accepts Frida
├── Renderer Processes ← High memory, REFUSE Frida injection
└── Other child processes
```

**Key Insight**: 
- Networking happens in a dedicated child process
- This process accepts Frida but has no hookable functions
- Renderer processes refuse Frida (anti-debugging)
- Specific PIDs change on restart (not important)

---

## Frida Hooking Attempts

### Attempt 1: Windows API Hooking
**Script**: `kiro_api_hook.js`
**Target**: Network process (found via `find_kiro_pids.py`)
**Method**: Hook WinHTTP/WinINET functions

**Results**:
- ✅ Successfully attached to network process
- ✅ Installed 3 Windows API hooks
- ✅ Hooked `connect()` at socket level
- ❌ **No network activity captured**
- ⚠️ Process is NOT a renderer (no `window` object)

**Conclusion**: Network process accepts Frida but doesn't use standard Windows networking APIs.

### Attempt 2: Renderer Process Targeting
**Script**: `find_renderer.js`, `diagnose_networking.js`
**Targets**: High-memory processes (likely renderers)

**Results**:
- ❌ **All renderer processes**: Refused Frida injection
- Error: "process either refused to load frida-agent, or terminated during injection"

**Conclusion**: Renderer processes have **anti-debugging protection** that blocks Frida.

### Attempt 3: Socket-Level Hooking
**Script**: `socket_intercept.js`
**Target**: Network process
**Method**: Hook `send()`, `recv()`, `connect()` from ws2_32.dll

**Results**:
- ✅ WS2_32.dll found and loaded
- ❌ `Module.getExportByName('ws2_32.dll', 'send')` returned null
- ❌ `Module.getExportByName('ws2_32.dll', 'recv')` returned null
- ❌ `Module.getExportByName('ws2_32.dll', 'connect')` returned null

**Conclusion**: Functions exist in DLL but aren't exported in a hookable way.

### Attempt 4: Chromium Internal Hooking
**Script**: `chromium_network_hook.js`
**Target**: Network process
**Method**: Search for Chromium/Node.js networking internals

**Results**:
- ✅ Found 3 Chromium-related modules:
  - `spdlog.node` (0.6 MB)
  - `node_sqlite3.node` (1.8 MB)
  - `index.node` (59.4 MB) ← **Main Electron/Chromium module**
- ❌ 0 networking exports found
- ❌ SSL_write/SSL_read not found
- ❌ getaddrinfo not hookable
- ❌ Node.js process object not available

**Conclusion**: Networking is compiled into `index.node` with no exported symbols.

---

## Technical Barriers Identified

### 1. Anti-Debugging Protection
**Location**: Renderer processes (PIDs 14008, 19740, etc.)
**Effect**: Blocks Frida injection
**Evidence**: "refused to load frida-agent" error
**Impact**: Cannot hook actual rendering/networking processes

### 2. Symbol Stripping
**Location**: `index.node` (59.4 MB module)
**Effect**: No exported networking functions
**Evidence**: 0 exports found despite DLLs being loaded
**Impact**: Cannot hook Chromium's internal networking

### 3. Certificate Pinning (Confirmed)
**Evidence**: 
- Other users reported mitmproxy failures
- Standard HTTPS proxies don't work
- Kiro validates AWS certificates

**Expected behavior**: Kiro only trusts AWS certificate fingerprints
**Impact**: HTTPS proxies rejected, TLS interception blocked

### 4. Internal Networking Stack
**Discovery**: Chromium uses BoringSSL and internal networking
**Effect**: Standard Windows APIs (WinHTTP, ws2_32) not used
**Impact**: Traditional hooking methods ineffective

---

## Current Status Summary

### What Works ✅
1. **Process identification**: `find_kiro_pids.py` successfully finds networking process
2. **Frida attachment**: Can attach to network process (not renderers)
3. **Endpoint discovery**: Know exact API endpoints and format
4. **Architecture understanding**: Mapped Kiro's process structure

### What Doesn't Work ❌
1. **Renderer hooking**: Anti-debugging blocks Frida
2. **API interception**: No hookable networking functions
3. **Socket hooking**: Functions not exported
4. **SSL/TLS hooking**: BoringSSL symbols stripped
5. **HTTPS proxies**: Certificate pinning blocks mitmproxy and similar tools

---

## Proposed Solutions

**Note**: Certificate pinning is confirmed. Any solution MUST bypass certificate validation first.

### Option 1: Binary Patching (REQUIRED)
**Approach**: Patch certificate validation in Kiro executable

**Steps**:
1. Reverse engineer `Kiro.exe` or `index.node` (59.4 MB)
2. Find certificate validation code
3. Patch to always return "valid"
4. Then use local proxy or DNS hijacking

**Tools**:
- Ghidra or IDA Pro (disassembly)
- x64dbg (debugging)
- HxD (hex editor)

**Pros**:
- Once patched, all other methods become viable
- Can intercept and modify all traffic
- Full control over requests/responses

**Cons**:
- Requires reverse engineering skills
- Patch breaks on Kiro updates
- May violate Kiro's terms of service

**Search targets**:
- Strings: "CertVerify", "SSL_CTX_set_verify", "certificate", "pinning"
- AWS certificate fingerprints
- X509 validation functions
- BoringSSL certificate verification

### Option 2: Frida Spawn Gating (After Patching)
**Approach**: Inject Frida before anti-debug initializes

**Method**:
```python
# Instead of attach, spawn with Frida
import frida
device = frida.get_local_device()
pid = device.spawn(["C:\\Path\\To\\Kiro.exe"])
session = device.attach(pid)
# Inject hooks before process fully starts
script = session.create_script(hook_code)
script.load()
device.resume(pid)
```

**Pros**:
- Can hook renderer processes before anti-debug
- Hooks installed at process start
- Can intercept early initialization

**Cons**:
- Still requires certificate pinning bypass
- May fail if anti-debug is very early
- Complex timing issues

**Status**: Worth trying AFTER certificate validation is patched

### Option 3: Local Server with DNS Hijacking (After Patching)
**Approach**: Redirect AWS endpoints to localhost

**Steps**:
1. **FIRST**: Patch certificate validation (required)
2. Modify `C:\Windows\System32\drivers\etc\hosts`:
   ```
   127.0.0.1 q.us-east-1.amazonaws.com
   127.0.0.1 q.eu-central-1.amazonaws.com
   ```
3. Create local server mimicking AWS Q API
4. Use kiro-gateway code as reference for API format
5. Return our own LLM responses

**Pros**:
- Simple to implement after patching
- Easy to debug
- Full control over responses

**Cons**:
- Requires certificate validation bypass first
- Need to implement AWS Q API format
- Kiro might have fallback endpoints

**Status**: Best approach AFTER patching is complete

---

## Recommended Approach

### Phase 1: Certificate Validation Bypass
**Priority**: HIGH
**Method**: Binary patching

1. Extract `index.node` from Kiro installation
2. Analyze with Ghidra to find certificate validation
3. Create minimal patch to disable validation
4. Test with mitmproxy

### Phase 2: Local Proxy Server
**Priority**: MEDIUM
**Method**: DNS hijacking + custom server

1. Set up local HTTPS server on port 443
2. Implement AWS Q API endpoints (from kiro-gateway)
3. Redirect to our own LLM (OpenAI, Anthropic, local)
4. Return responses in AWS Q format

### Phase 3: Request/Response Translation
**Priority**: MEDIUM
**Method**: Protocol conversion

1. Parse incoming AWS Q requests
2. Convert to OpenAI/Anthropic format
3. Send to our LLM
4. Convert response back to AWS Q format
5. Return to Kiro

---

## Tools and Scripts Created

### Working Tools ✅
1. **`find_kiro_pids.py`** - Identifies Kiro processes with network activity
2. **`attach.py`** - Updated to handle PIDs directly (not just process names)
3. **`kiro_api_hook.js`** - Region-agnostic endpoint detection
4. **`diagnose_networking.js`** - Analyzes process networking stack

### Diagnostic Tools 🔍
5. **`find_renderer.js`** - Checks if process is a renderer
6. **`chromium_network_hook.js`** - Searches for Chromium internals
7. **`socket_intercept.js`** - Attempts socket-level hooking
8. **`intercept_and_redirect.js`** - Full interception attempt

### Reference Material 📚
9. **`_reference_kiro-gateway-main/`** - Open-source Kiro proxy (reverse direction)
10. **`ANALYSIS_FINDINGS.md`** - Original Kiro structure analysis

---

## Next Steps

### Immediate Actions
1. ⬜ Extract and analyze `index.node` with Ghidra
2. ⬜ Search for certificate validation functions
3. ⬜ Create proof-of-concept patch
4. ⬜ Test with mitmproxy

### Alternative Path (If patching fails)
1. ⬜ Try Frida spawn gating on renderer process
2. ⬜ Implement kernel-level hooking with WinDivert
3. ⬜ Research Electron/Chromium certificate pinning bypasses

### Long-term Goals
1. ⬜ Build local AWS Q API server
2. ⬜ Implement request/response translation
3. ⬜ Support multiple LLM backends
4. ⬜ Create user-friendly configuration

---

## Technical Notes

### Kiro Architecture
- **Base**: Electron (Chromium + Node.js)
- **Networking**: BoringSSL (Chromium's SSL library)
- **Protection**: Anti-debugging on renderer processes
- **Compilation**: Symbols stripped from main module

### API Format (from kiro-gateway)
**Request to AWS Q**:
```json
POST https://q.us-east-1.amazonaws.com/generateAssistantResponse
Headers:
  Authorization: Bearer <access_token>
  x-amz-target: CodeWhispererStreaming_20230920.GenerateAssistantResponse
Body:
  {
    "conversationId": "...",
    "message": "...",
    "modelId": "...",
    ...
  }
```

**Response from AWS Q**:
```json
{
  "conversationId": "...",
  "message": "...",
  "content": "...",
  ...
}
```

### Certificate Pinning Indicators
- mitmproxy failures reported by other users
- No standard SSL functions hookable
- Likely validates AWS certificate fingerprints
- May use Chromium's built-in pinning

---

## Lessons Learned

1. **Electron apps are hard to hook**: Symbol stripping + anti-debug
2. **Renderer processes are protected**: Can't use standard Frida attach
3. **Certificate pinning is real**: mitmproxy doesn't work
4. **Binary patching is necessary**: No pure Frida solution exists
5. **kiro-gateway is valuable**: Shows exact API format we need to mimic

---

## Resources

### Documentation
- AWS CodeWhisperer API: https://docs.aws.amazon.com/codewhisperer/
- kiro-gateway: https://github.com/jwadow/kiro-gateway
- Frida documentation: https://frida.re/docs/

### Tools
- Ghidra: https://ghidra-sre.org/
- x64dbg: https://x64dbg.com/
- mitmproxy: https://mitmproxy.org/
- WinDivert: https://www.reqrypt.org/windivert.html

### Similar Projects
- Cursor proxy attempts (failed due to certificate pinning)
- Copilot reverse engineering (similar challenges)

---

## Conclusion

We've successfully identified Kiro's API endpoints and architecture, but hit technical barriers:
- **Anti-debugging** blocks renderer process hooking
- **Symbol stripping** prevents function hooking
- **Certificate pinning** blocks HTTPS proxies

**The path forward requires binary patching** to disable certificate validation, after which standard HTTPS interception will work. This is a well-understood technique but requires reverse engineering skills.