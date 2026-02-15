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
- Successfully attached to network process
- Installed 3 Windows API hooks
- Hooked `connect()` at socket level
- **No network activity captured**
- Process is NOT a renderer (no `window` object)

**Conclusion**: Network process accepts Frida but doesn't use standard Windows networking APIs.

### Attempt 2: Renderer Process Targeting
**Script**: `find_renderer.js`, `diagnose_networking.js`
**Targets**: High-memory processes (likely renderers)

**Results**:
- **All renderer processes**: Refused Frida injection
- Error: "process either refused to load frida-agent, or terminated during injection"

**Conclusion**: Renderer processes have **anti-debugging protection** that blocks Frida.

### Attempt 3: Socket-Level Hooking
**Script**: `socket_intercept.js`
**Target**: Network process
**Method**: Hook `send()`, `recv()`, `connect()` from ws2_32.dll

**Results**:
- WS2_32.dll found and loaded
- `Module.getExportByName('ws2_32.dll', 'send')` returned null
- `Module.getExportByName('ws2_32.dll', 'recv')` returned null
- `Module.getExportByName('ws2_32.dll', 'connect')` returned null

**Conclusion**: Functions exist in DLL but aren't exported in a hookable way.

### Attempt 4: Chromium Internal Hooking
**Script**: `chromium_network_hook.js`
**Target**: Network process
**Method**: Search for Chromium/Node.js networking internals

**Results**:
- Found 3 Chromium-related modules:
  - `spdlog.node` (0.6 MB)
  - `node_sqlite3.node` (1.8 MB)
  - `index.node` (59.4 MB) - **Main Electron/Chromium module**
- 0 networking exports found
- SSL_write/SSL_read not found
- getaddrinfo not hookable
- Node.js process object not available

**Conclusion**: Networking is compiled into `index.node` with no exported symbols.

### Attempt 5: Frida Spawn Gating
**Date**: 2026-02-15
**Script**: `attach.py --spawn`
**Target**: All Kiro processes from startup
**Method**: Spawn Kiro with Frida, inject hooks before anti-debug initializes

**Results**:
- Successfully spawned Kiro (PID 7444)
- Hooks injected before process resume
- 11 total processes detected
- 8 processes successfully hooked (73% success rate)
- 3 processes refused hooks (27% failure rate)

**Processes that refused hooks**:
- PID 19596 (293.3 MB memory)
- PID 20128 (427.1 MB memory) - highest memory usage
- PID 21576 (275.7 MB memory)
- PID 22948 (150.3 MB memory)

**Network detection**:
- psutil unable to detect any AWS connections
- User confirmed AI features were triggered during test
- No network activity captured by hooks

**Analysis**:
- Refused processes are high-memory renderer processes
- These processes have stronger anti-debug protection
- Spawn gating bypassed anti-debug on 8 processes but not renderers
- Networking likely occurs in one of the refused renderer processes
- psutil cannot see connections (hidden or using undetectable method)

**Conclusion**: Spawn gating successfully bypasses anti-debug on most processes but fails on renderer processes where networking actually occurs. The renderer processes have layered anti-debug protection that activates even before Frida can inject hooks.

---

## Technical Barriers Identified

### 1. Anti-Debugging Protection
**Location**: Renderer processes (high-memory child processes)
**Effect**: Blocks Frida injection even with spawn gating
**Evidence**: 
- "refused to load frida-agent" error on attach
- Spawn gating bypasses protection on 73% of processes
- Renderer processes (27%) still refuse hooks
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

### 5. Hidden Network Connections
**Discovery**: psutil cannot detect active AWS connections
**Evidence**: 
- User confirmed AI features triggered during test
- No connections visible via psutil.net_connections()
- Hooks installed but no traffic captured
**Impact**: Cannot identify which process handles networking from outside

---

## Current Status Summary

### What Works
1. **Process identification**: `find_kiro_pids.py` successfully finds Kiro processes
2. **Frida attachment**: Can attach to non-renderer processes
3. **Spawn gating**: Successfully hooks 73% of processes before anti-debug initializes
4. **Endpoint discovery**: Know exact API endpoints and format
5. **Architecture understanding**: Mapped Kiro's process structure

### What Doesn't Work
1. **Renderer hooking**: Anti-debug blocks Frida even with spawn gating
2. **API interception**: No hookable networking functions in accessible processes
3. **Socket hooking**: Functions not exported
4. **SSL/TLS hooking**: BoringSSL symbols stripped
5. **HTTPS proxies**: Certificate pinning blocks mitmproxy and similar tools
6. **Network detection**: psutil cannot see active AWS connections

---

## Breakthrough: Certificate Bypass Success

### Command-Line Flags Approach
**Method**: Launch Kiro with Chromium flags to disable certificate validation

After exploring binary patching and complex modification approaches, we tested the simplest solution: Chromium's built-in certificate bypass flags.

**Implementation**:
```batch
Kiro.exe --ignore-certificate-errors --proxy-server="127.0.0.1:99974"
```

Combined with environment variables:
```batch
set NODE_TLS_REJECT_UNAUTHORIZED=0
set ELECTRON_IGNORE_CERTIFICATE_ERRORS=1
```

**Result**: Complete success. The flags bypassed all certificate validation without any file modifications.

### Traffic Interception Achieved

**Setup**:
1. Started mitmproxy on dedicated port (99974)
2. Launched Kiro with `--proxy-server` flag (only Kiro traffic proxied, system unaffected)
3. Used CLI launcher mode which properly opens GUI

**Captured Traffic**:

Successfully intercepted AWS Q API calls:

```
POST https://q.us-east-1.amazonaws.com/generateAssistantResponse

Headers:
  Authorization: Bearer [token]
  content-type: application/json
  user-agent: aws-sdk-js/1.0.27 ua/2.1 os/win32 lang/js md/nodejs api/codewhispererstreaming

Body (Plaintext JSON):
{
  "conversationState": {
    "agentContinuationId": "uuid",
    "agentTaskType": "vibe",
    "chatTriggerType": "MANUAL",
    "conversationId": "uuid",
    "currentMessage": {
      "userInputMessage": {
        "content": "user message"
      }
    }
  }
}
```

**Key Findings**:
- API endpoint confirmed: `q.us-east-1.amazonaws.com`
- Authentication: Bearer token in Authorization header
- User agent identifies as `aws-sdk-js` with CodeWhisperer streaming API
- **Request format**: Plaintext JSON with full conversation state structure
- **Response format**: Unknown encoding (appears binary in proxy, plaintext in Kiro UI)
- Telemetry also captured: `prod.us-east-1.telemetry.desktop.kiro.dev`

**Request Body Structure**:
```json
{
  "conversationState": {
    "agentContinuationId": "string (uuid)",
    "agentTaskType": "string (e.g., 'vibe')",
    "chatTriggerType": "string (e.g., 'MANUAL')",
    "conversationId": "string (uuid)",
    "currentMessage": {
      "userInputMessage": {
        "content": "string (user's message)"
      }
    }
  }
}
```

### Response Decoding Strategy

**Challenge**: Responses appear as binary/encoded in proxy logs, but Kiro displays plaintext AI responses in UI.

**Approach**: 
1. Capture response data with enhanced proxy
2. Copy plaintext response from Kiro UI
3. Compare captured data with UI plaintext to identify encoding
4. Determine format: event-stream, GZIP, protobuf, or other
5. Build decoder for response format

**Enhanced proxy features**:
- JSON pretty-printing for requests
- Multiple decoding strategies for responses (JSON, text, event-stream, GZIP)
- Auto-save to `captured_requests.jsonl` and `captured_responses.jsonl`
- Binary response saved to `response_binary_*.bin` files
- Analysis tool: `analyze_responses.py` for comparing captured data

**Testing Process**:
1. Run `Kiro-CLI-NoSSL.bat` to start proxy and Kiro
2. Send test message in Kiro AI chat
3. Copy AI's plaintext response from Kiro UI
4. Run `python frida-scripts/analyze_responses.py` to view captured data
5. Compare captured response format with UI plaintext
6. Identify encoding type and build decoder

---

## Response Format Investigation

### Current Phase: Response Decoding

**Objective**: Identify how AWS Q API encodes response data

**Known Facts**:
- Requests are plaintext JSON (confirmed and documented)
- Responses display as plaintext in Kiro UI
- Responses may appear encoded/binary in proxy capture
- Need to compare captured data with UI plaintext to identify encoding

**Testing Setup**:
1. Enhanced proxy with multiple decoding strategies
2. Auto-capture to `captured_requests.jsonl` and `captured_responses.jsonl`
3. Binary responses saved to `response_binary_*.bin` files
4. Analysis tool ready: `analyze_responses.py`

**Next Test Run**:
1. Launch: `Kiro-CLI-NoSSL.bat`
2. Send test message in Kiro
3. Copy AI response from UI
4. Run: `python frida-scripts/analyze_responses.py`
5. Compare formats to identify encoding

**Possible Response Formats**:
- Server-Sent Events (text/event-stream) - streaming responses
- GZIP compressed JSON
- Protocol Buffers (binary)
- Plain JSON (if proxy decodes automatically)
- Custom binary format

### Final Implementation

**Unified Launcher**: `Kiro-CLI-NoSSL.bat`

This single script:
1. Checks for Python and mitmproxy
2. Starts mitmproxy on port 99974 in background window
3. Waits for proxy initialization
4. Launches Kiro with certificate bypass and proxy configuration
5. Only Kiro traffic is proxied (system proxy unchanged)

**Key advantages**:
- No system-wide proxy configuration needed
- No file modifications to Kiro
- Works across Kiro updates
- Easy to enable/disable (just use different launcher)
- Clean separation of concerns

---

## Current Status Summary

### What Works
1. **Certificate bypass**: Chromium flags successfully disable validation
2. **Traffic interception**: Full HTTPS interception via mitmproxy
3. **Request visibility**: Complete plaintext JSON request capture
4. **Isolated proxy**: Only Kiro traffic affected, system unchanged
5. **Endpoint discovery**: Confirmed AWS Q API format and structure
6. **Architecture understanding**: Mapped Kiro's process structure

### What's In Progress
1. **Response decoding**: Identifying binary response format
2. **Format comparison**: Using Kiro UI plaintext to reverse engineer encoding
3. **API documentation**: Building complete request/response schema

### What We Learned
1. **Simplest solution won**: Command-line flags worked where complex hooking failed
2. **CLI launcher works**: Using CLI mode properly launches GUI with all flags
3. **Proxy isolation**: `--proxy-server` flag routes only app traffic
4. **No modifications needed**: Kiro binaries remain untouched
5. **Frida unnecessary**: For interception, certificate bypass alone is sufficient
6. **Request format is simple**: Plaintext JSON, easy to replicate
7. **Response needs decoding**: Binary format requires reverse engineering

---

## Next Steps

### Phase 1: Response Format Identification (Current)
1. Capture response data with enhanced proxy
2. Copy plaintext AI response from Kiro UI
3. Compare binary data with plaintext to identify encoding
4. Determine if format is: event-stream, GZIP, protobuf, or other
5. Build decoder for response format

### Phase 2: API Documentation
1. Document complete request structure with all fields
2. Document decoded response structure
3. Identify required vs optional fields
4. Map conversation state management
5. Document authentication token format and refresh mechanism

### Phase 3: Local Mock Server
1. Build Flask/FastAPI server mimicking AWS Q API
2. Implement `/generateAssistantResponse` endpoint
3. Parse incoming requests
4. Return responses in correct format
5. Test with Kiro to verify acceptance

### Phase 4: OpenAI Bridge
1. Translate AWS Q requests to OpenAI API v1 format
2. Connect to OpenAI/Anthropic/local LLM
3. Translate responses back to AWS Q format
4. Handle streaming if needed
5. Full end-to-end testing

### Phase 5: Telemetry Filtering
1. Identify telemetry endpoints
2. Block or mock telemetry responses
3. Ensure Kiro functions without telemetry

---

## Conclusion

After extensive exploration of Frida hooking, spawn gating, and binary analysis, the solution was surprisingly simple: Chromium's built-in certificate bypass flags combined with the `--proxy-server` parameter. This approach:

- Requires no file modifications
- Works across updates
- Provides complete traffic visibility
- Maintains system stability

The key insight was using the CLI launcher mode, which properly passes all flags to the GUI application. We now have full visibility into Kiro's AWS Q API communication and can proceed with building a local replacement server.

---

## Tools and Scripts

### Active Tools
- **`Kiro-CLI-NoSSL.bat`** - Unified launcher (starts proxy + Kiro with interception)
- **`frida-scripts/test_proxy.py`** - Enhanced mitmproxy with response decoding
- **`frida-scripts/analyze_responses.py`** - Analyzes captured data and compares formats

### Captured Data Files
- **`captured_requests.jsonl`** - All AWS Q requests (JSON Lines format)
- **`captured_responses.jsonl`** - All AWS Q responses (JSON Lines format)
- **`response_binary_*.bin`** - Binary responses for analysis

### Development Tools (Historical)
- **`find_kiro_pids.py`** - Process identification
- **`attach.py`** - Frida attachment and spawn gating
- **`kiro_api_hook.js`** - Frida hooking attempts
- Various diagnostic scripts for exploration phase

### Reference Material
- **`_reference_kiro-gateway-main/`** - Open-source Kiro proxy (reverse direction)
- **`ANALYSIS_FINDINGS.md`** - Original Kiro structure analysis

---

## Next Actions

1. **Decode response format** - Run test capture and compare with Kiro UI plaintext
2. **Document complete API** - Build full request/response schema
3. **Build mock server** - Create local AWS Q API endpoint
4. **Test response acceptance** - Verify Kiro accepts our responses
5. **Build OpenAI bridge** - Translate between AWS Q and OpenAI API formats
6. **Filter telemetry** - Block unnecessary telemetry traffic

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

1. **Start simple**: Command-line flags solved what complex hooking couldn't
2. **Electron apps respect Chromium flags**: `--ignore-certificate-errors` works universally
3. **CLI launcher mode**: Properly passes flags to GUI application
4. **Isolated proxying**: `--proxy-server` flag avoids system-wide configuration
5. **Frida has limits**: Anti-debug protection in renderers is strong, but unnecessary for this goal
6. **Certificate pinning bypassed**: Chromium flags override application-level pinning
7. **Network detection limitations**: psutil can't see Chromium's internal connections, but proxy interception works perfectly

---

## Resources

### Documentation
- AWS CodeWhisperer API: https://docs.aws.amazon.com/codewhisperer/
- kiro-gateway: https://github.com/jwadow/kiro-gateway
- Chromium Command Line Switches: https://peter.sh/experiments/chromium-command-line-switches/

### Tools Used
- mitmproxy: https://mitmproxy.org/
- Python 3.x
- Windows batch scripting

---

## Conclusion

We've successfully identified Kiro's API endpoints and architecture, and developed spawn gating to bypass anti-debug on most processes. However, critical technical barriers remain:

- **Anti-debugging** blocks renderer process hooking even with spawn gating (27% of processes refuse)
- **Symbol stripping** prevents function hooking in accessible processes
- **Certificate pinning** blocks HTTPS proxies
- **Hidden connections** prevent external network detection

**Key Finding**: Spawn gating successfully bypasses anti-debug on 73% of Kiro processes, but the renderer processes where networking occurs have layered protection that activates before Frida injection. The networking happens in high-memory renderer processes (250-450 MB) that refuse all hooking attempts.

**The path forward requires binary patching** to disable certificate validation and anti-debug protection in the renderer processes. This is a well-understood technique but requires reverse engineering skills and breaks on Kiro updates.


---

## Response Format Decoded - AWS Event Stream

### Format Identified
**AWS Event Stream** - Binary streaming protocol used by AWS services

**Event Types**:
1. **assistantResponseEvent** - Text chunks: `{"content": "text"}`
2. **toolUseEvent** - Tool calls (streamed): `{"name": "tool", "toolUseId": "id", "input": "json chunk"}`
3. **meteringEvent** - Usage: `{"unit": "credit", "usage": 0.214}`
4. **contextUsageEvent** - Context: `{"contextUsagePercentage": 53.54}`

### Tools Created
- `decode_event_stream.py` - Decodes binary AWS Event Stream to JSON
- `reconstruct_messages.py` - Rebuilds full messages from event chunks
- `BRIDGE_DESIGN.md` - Architecture for API bridge to standard LLM APIs

### Next Phase: API Bridge
Build local server to translate AWS Q ↔ Anthropic/OpenAI/Local LLMs

**Why Anthropic format**: AWS Q is clearly based on Claude (tool use, streaming match)

**Bridge Components**:
1. Event Stream encoder (AWS Q response format)
2. Request translator (AWS Q → Anthropic)
3. Response translator (Anthropic → AWS Q Event Stream)
4. Bridge server (FastAPI)
5. Proxy integration (forward to bridge instead of AWS)

**Goal**: Use any LLM backend while Kiro thinks it's talking to AWS Q

---

## Project Restructure and Finalization

### Directory Structure
Reorganized for cleaner architecture:
```
kiro-conduit/
├── kiropipe.py              # Main launcher script
├── Kiro/Kiro.exe            # Kiro executable
└── _kiropipe/               # All modules and data
    ├── debug_logs/
    │   └── interactions/
    │       ├── responses/   # Response files
    │       └── posted/      # Request files
    └── (bridge modules - future)
```

### Unified Launcher Features
**Configuration** (top of `kiropipe.py`):
- `DEFAULT_PORT = 29974` - Proxy port (under 34438 limit)
- `KIRO_EXE_PATH = None` - Custom path or auto-detect
- `BLOCK_TELEMETRY = True` - Block all telemetry (any region)
- `BLOCK_UPDATES = True` - Block update checks
- `BLOCK_USAGE_LIMITS = False` - Block usage limit checks (optional)
- `DEBUG_MODE = True` - Toggle detailed logging

**Auto-Detection**:
- Finds Kiro.exe in multiple locations:
  1. Custom `KIRO_EXE_PATH` (if set)
  2. `Kiro/Kiro.exe` (subfolder)
  3. `Kiro.exe` (same folder)
  4. Current working directory

**Debug Mode**:
- When `True`: Detailed console output + file logging
- When `False`: Silent operation, no files saved
- Files organized in `_kiropipe/debug_logs/interactions/`

**Blocking Verified**:
- Telemetry: Successfully blocks metrics and traces (any region)
- Updates: Blocks version checks
- Usage limits: Removes credit consumption display (optional)

### Testing Results
- Certificate bypass working across all regions
- Traffic interception successful
- Binary responses decoded to readable JSON
- Tool use events captured and decoded
- Streaming responses reconstructed
- All blocking features functional

### Current Status
**Complete**:
1. ✅ Traffic interception with certificate bypass
2. ✅ AWS Event Stream format decoded
3. ✅ Request/response logging with debug mode
4. ✅ Telemetry and update blocking
5. ✅ Organized file structure
6. ✅ Flexible Kiro.exe detection
7. ✅ Complete API format documentation

**Ready for Next Phase**:
- Build API bridge server
- Implement AWS Event Stream encoder
- Add LiteLLM integration for universal LLM support
- Support free models (Ollama, Groq, etc.)

---

## Next Steps: API Bridge Implementation

### Phase 1: AWS Event Stream Encoder
Create encoder to generate binary responses matching AWS format

### Phase 2: Request Translator
Convert AWS Q requests to Anthropic/OpenAI format

### Phase 3: Response Translator  
Convert LLM responses back to AWS Event Stream

### Phase 4: Bridge Server
FastAPI server that proxies and translates requests

### Phase 5: Integration
Update proxy to forward to local bridge instead of AWS

### Phase 6: LiteLLM Support
Add universal LLM support (100+ providers)

### Phase 7: Free Model Support
Configure for Ollama, Groq, and other free options

---

## Tools and Scripts

### Active Tools
- **`kiropipe.py`** - Unified launcher (proxy + Kiro with interception)
- **`_kiropipe/decode_event_stream.py`** - Decode binary responses
- **`_kiropipe/reconstruct_messages.py`** - Rebuild full messages
- **`_kiropipe/BRIDGE_DESIGN.md`** - Bridge architecture document

### Configuration
All settings in top of `kiropipe.py`:
- Port, paths, blocking options, debug mode
- No command-line arguments needed
- Restart script to apply changes

### Debug Output
When `DEBUG_MODE = True`:
- Console: Detailed request/response logging
- Files: `_kiropipe/debug_logs/interactions/`
  - `posted/` - Request JSON files
  - `responses/` - Response binary/JSON files

---

## Key Learnings

1. **Port limitation**: mitmproxy ports must be ≤34438
2. **Certificate bypass**: Chromium flags work universally
3. **AWS Event Stream**: Binary streaming protocol, not text
4. **Tool use**: Streamed as chunks, must be concatenated
5. **Blocking**: Region-agnostic patterns work across all AWS regions
6. **Debug mode**: Essential for development, disable for production
7. **File organization**: Centralized `_kiropipe/` keeps everything clean
