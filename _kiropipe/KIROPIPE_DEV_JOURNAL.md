# Kiro Network Interception - Technical Journal

## Project Goal
Intercept Kiro's AWS Q API traffic and redirect to custom LLM backends (Anthropic, OpenAI, local models).

---

## Phase 1: Endpoint Discovery

### Method
Analyzed open-source `kiro-gateway` project for API structure.

### Findings
- Service: AWS CodeWhisperer/Amazon Q (not AWS Bedrock)
- Endpoint: `https://q.{region}.amazonaws.com`
- Primary API: `/generateAssistantResponse`
- Authentication: Bearer token via `Authorization` header
- Default region: `us-east-1`

---

## Phase 2: Interception Approach

### Initial Attempts - Frida Hooking
Attempted multiple Frida-based approaches:
- Windows API hooking (WinHTTP/WinINET)
- Socket-level hooking (ws2_32.dll)
- Chromium internal hooking
- Spawn gating

**Result**: Failed. Renderer processes have anti-debug protection that blocks Frida injection. Networking occurs in protected renderer processes with no hookable exports.

### Successful Approach - Certificate Bypass
Used Chromium's built-in flags to disable certificate validation:

```bash
Kiro.exe --ignore-certificate-errors \
         --ignore-certificate-errors-spki-list \
         --proxy-server="127.0.0.1:29974"
```

Combined with environment variables:
```bash
NODE_TLS_REJECT_UNAUTHORIZED=0
ELECTRON_IGNORE_CERTIFICATE_ERRORS=1
```

**Result**: Complete HTTPS interception via mitmproxy without modifying Kiro binaries.

**Key Insight**: CLI launcher mode (`cli.js`) properly passes flags to GUI application.

---

## Phase 3: Traffic Analysis

### Request Format
Plaintext JSON with conversation state:

```json
POST /generateAssistantResponse
{
  "conversationState": {
    "conversationId": "uuid",
    "agentContinuationId": "uuid",
    "agentTaskType": "vibe",
    "chatTriggerType": "MANUAL",
    "currentMessage": {
      "userInputMessage": {
        "content": "user message",
        "modelId": "auto",
        "origin": "AI_EDITOR",
        "userInputMessageContext": {
          "toolResults": [...],
          "tools": [...]
        }
      }
    }
  }
}
```

### Response Format
Binary streaming protocol: AWS Event Stream

**Event Types**:
1. `assistantResponseEvent` - Text content chunks
   ```json
   {"content": "text chunk"}
   ```

2. `toolUseEvent` - Tool call chunks (streamed)
   ```json
   {"name": "toolName", "toolUseId": "id", "input": "partial json"}
   ```

3. `meteringEvent` - Usage tracking
   ```json
   {"unit": "credit", "usage": 0.214}
   ```

4. `contextUsageEvent` - Context window usage
   ```json
   {"contextUsagePercentage": 53.54}
   ```

**Binary Structure**:
- Prelude: 12 bytes (total length, headers length, CRC)
- Headers: Key-value pairs (event-type, content-type, message-type)
- Payload: JSON data
- Message CRC: 4 bytes

**Decoding**: Custom Python decoder successfully parses binary format. Full messages reconstructed by concatenating content chunks.

---

## Phase 4: Implementation

### Architecture
```
kiropipe.py (launcher)
    ↓
mitmproxy (port 29974)
    ↓
Kiro.exe (with certificate bypass)
    ↓
AWS Q API (intercepted)
```

### Directory Structure
```
kiro-conduit/
├── kiropipe.py              # Main launcher
├── Kiro/Kiro.exe            # Kiro executable
└── _kiropipe/               # Modules and data
    ├── debug_logs/
    │   └── interactions/
    │       ├── responses/   # Binary responses
    │       └── posted/      # Requests
    └── (tools and bridge modules)
```

### Configuration
All settings in `kiropipe.py`:
- `DEFAULT_PORT = 29974` (mitmproxy limit: ≤34438)
- `KIRO_EXE_PATH = None` (auto-detect or custom path)
- `BLOCK_TELEMETRY = True` (blocks metrics/traces, any region)
- `BLOCK_UPDATES = True` (blocks version checks)
- `BLOCK_USAGE_LIMITS = False` (optional, removes credit display)
- `DEBUG_MODE = True` (toggle logging and file output)

### Features
- Auto-detects Kiro.exe in multiple locations
- Region-agnostic blocking (works across all AWS regions)
- Debug mode: detailed logging + file capture
- Production mode: silent operation, no files
- Single script execution, no system-wide proxy changes

---

## Phase 5: Tools Developed

### Core Engine Scripts (_kiropipe/engine/)

**decode_event_stream.py** - Decodes AWS Event Stream binary format to JSON.
```bash
python _kiropipe/engine/decode_event_stream.py
```

**event_stream_encoder.py** - Encodes responses to AWS Event Stream format.
```bash
python _kiropipe/engine/event_stream_encoder.py
```

**reconstruct_messages.py** - Rebuilds full messages from event chunks.
```bash
python _kiropipe/engine/reconstruct_messages.py
```

### Development Tools (_kiropipe/tools/)

**test_encoder.py** - Tests encoder/decoder round-trip and validates format.
```bash
python _kiropipe/tools/test_encoder.py
```

**analyze_interaction_pattern.py** - Analyzes request/response patterns.
```bash
python _kiropipe/tools/analyze_interaction_pattern.py
```

---

## Technical Findings

### Port Limitation
mitmproxy ports must be ≤34438. Higher ports are ignored.

### Certificate Pinning
Chromium flags override application-level certificate pinning. No binary patching required.

### Streaming Protocol
AWS Q uses streaming responses similar to Anthropic Claude API, indicating shared architecture.

### Tool Use Format
Tool calls are streamed as chunks. Input JSON must be concatenated from multiple events.

### Blocking Patterns
Using hostname substrings (e.g., 'telemetry') works across all regions without hardcoding region names.

---

## Current Status

### Working
- Traffic interception with certificate bypass
- Request/response capture and logging
- AWS Event Stream decoding
- Telemetry, update, and usage limit blocking
- Debug mode with organized file structure
- Complete API format documentation

### Verified
- Certificate bypass works across Kiro updates
- No Kiro binary modifications required
- Only Kiro traffic proxied (system unaffected)
- Blocking functional for all tested features

---

## Next Phase: API Bridge

### Objective
Build local server to translate between AWS Q API and standard LLM APIs.

### Target Format
Primary: Anthropic Claude API (AWS Q is based on Claude architecture)
Secondary: OpenAI API (via LiteLLM adapter)

### Components
1. AWS Event Stream encoder (generate binary responses)
2. Request translator (AWS Q → Anthropic/OpenAI)
3. Response translator (Anthropic/OpenAI → AWS Event Stream)
4. Bridge server (FastAPI)
5. Proxy integration (forward to bridge instead of AWS)

### LLM Support
Using LiteLLM for universal compatibility:
- Anthropic (Claude)
- OpenAI (GPT)
- Ollama (local models)
- Groq (free tier)
- 100+ other providers

### Free Model Options
**Local**:
- Ollama + Llama 3.2 (3B/8B)
- Ollama + Qwen 2.5 Coder (7B)
- LM Studio

**Cloud**:
- Groq (14,400 requests/day free)
- Together AI (free credits)
- OpenRouter (free models)

### Implementation Plan
1. Implement AWS Event Stream encoder
2. Build request translator (AWS Q → target format)
3. Build response translator (target format → AWS Event Stream)
4. Create bridge server (FastAPI)
5. Update proxy to forward to bridge
6. Add LiteLLM integration
7. Test with multiple backends
8. Document configuration

---

## References

### Documentation
- AWS CodeWhisperer API: https://docs.aws.amazon.com/codewhisperer/
- kiro-gateway: https://github.com/jwadow/kiro-gateway
- Chromium Command Line Switches: https://peter.sh/experiments/chromium-command-line-switches/
- LiteLLM: https://github.com/BerriAI/litellm

### Tools
- mitmproxy: https://mitmproxy.org/
- Python 3.x
- FastAPI (planned)
- LiteLLM (planned)
