# KiroPipe Development Journal

## Project Goal
Intercept Kiro's AWS Q API traffic and redirect to custom LLM backends (Anthropic, OpenAI, Ollama, Groq, etc.).

---

## Phase 1: Endpoint Discovery

### Method
Analyzed open-source `kiro-gateway` project for API structure.

### Findings
- Service: AWS CodeWhisperer/Amazon Q
- Endpoint: `https://q.{region}.amazonaws.com`
- Primary API: `/generateAssistantResponse`
- Authentication: Bearer token via `Authorization` header
- Default region: `us-east-1`

---

## Phase 2: Interception Approach
Users had reported pinning certificates and being unable to sift through with MITM.

### Failed: Frida Hooking
Attempted multiple approaches:
- Windows API hooking (WinHTTP/WinINET)
- Socket-level hooking (ws2_32.dll)
- Chromium internal hooking
- Spawn gating

**Result**: Renderer processes have anti-debug protection blocking Frida injection.

### Success: Certificate Bypass
Users had reUsed Chromium flags to disable certificate validation and use MITM.

```bash
Kiro.exe --ignore-certificate-errors \
         --proxy-server="127.0.0.1:29974"
```

Environment variables:
```bash
NODE_TLS_REJECT_UNAUTHORIZED=0
ELECTRON_IGNORE_CERTIFICATE_ERRORS=1
```

**Result**: Complete HTTPS interception via mitmproxy without binary modifications.
**Key**: CLI launcher mode (`cli.js`) passes flags to GUI.

---

## Phase 3: Traffic Analysis

### Request Format
Plaintext JSON with conversation state:
- `conversationState.currentMessage.userInputMessage.content` - User message
- `conversationState.history` - Full conversation (200+ items, 500KB+)
- `userInputMessageContext.tools` - Available tools (wrapped in `toolSpecification`)
- `userInputMessageContext.toolResults` - Tool execution results (content as array)

### Response Format
Binary AWS Event Stream protocol.

**Event Types**:
1. `assistantResponseEvent` - Text chunks
2. `toolUseEvent` - Tool calls (streamed as JSON chunks)
3. `meteringEvent` - Usage tracking
4. `contextUsageEvent` - Context window percentage

**Binary Structure**:
- Prelude: 12 bytes (lengths + CRC)
- Headers: Key-value pairs
- Payload: JSON data
- Message CRC: 4 bytes

**Key Discovery**: Tool calls come FROM LLM (not from Kiro). Kiro executes tools locally and sends results in next request.

---

## Phase 4: Core Implementation

### Architecture
```
kiropipe.py → mitmproxy → Kiro.exe → AWS Q (intercepted)
```

### Features Implemented
- Auto-detect Kiro.exe location
- Region-agnostic blocking (telemetry, updates, usage limits)
- Debug mode with file capture
- Process monitoring (detects Kiro window, exits when closed)
- Injection queue system for testing

### Configuration System
Migrated from hardcoded variables to YAML:
- `kiropipe_config.yaml` - Main configuration
- Supports multiple providers with model aliases
- Dynamic usage limits based on model type
- Kiro endpoint control (TRUE=allow, FALSE=block)

---

## Phase 5: AWS Event Stream Codec

### Decoder (`decode_event_stream.py`)
Parses binary AWS Event Stream to JSON events.

**Capabilities**:
- Extracts all event types
- Validates CRC checksums
- Handles streaming chunks

### Encoder (`event_stream_encoder.py`)
Generates AWS Event Stream binary from events.

**Functions**:
- `encode_text_chunk()` - Text responses
- `encode_tool_use_chunk()` - Tool calls (streamed)
- `encode_metering()` - Usage metrics
- `encode_context_usage()` - Context percentage

**Validation**: Round-trip encoding/decoding verified against captured AWS Q responses.

---

## Phase 6: API Bridge

### Request Translator (`request_translator.py`)
Converts AWS Q format to standard LLM APIs.

**Anthropic Translation**:
- Extracts conversation history from `conversationState.history`
- Unwraps tools from `toolSpecification` wrapper
- Extracts text from tool results content array
- Builds Anthropic Messages API format

**OpenAI Translation**:
- Similar extraction logic
- Converts to Chat Completions format
- Handles tool results as separate messages

### Response Translator (`response_translator.py`)
Converts LLM streaming responses to AWS Event Stream.

**Anthropic Stream**:
- `message_start` → Extract input tokens
- `content_block_delta` (text) → `assistantResponseEvent`
- `content_block_delta` (tool) → `toolUseEvent` (streamed)
- `message_delta` → Extract output tokens
- `message_stop` → `meteringEvent` + `contextUsageEvent`

**OpenAI Stream**:
- Similar mapping for OpenAI SSE format
- Handles tool calls accumulation
- Generates usage events

### Bridge Server (`bridge_server.py`)
FastAPI server with endpoints:
- `POST /generateAssistantResponse` - Main API (mimics AWS Q)
- `GET /health` - Status + statistics
- `GET /config` - Current configuration
- `GET /stats` - Detailed usage per session

**Backends Supported**:
- Anthropic (direct API)
- OpenAI (direct API)
- LiteLLM (universal - 100+ providers)

**Session Tracking**:
- Per-conversation statistics
- Token usage tracking
- Request counting

---

## Phase 7: LiteLLM Integration

### Purpose
Single bridge implementation supporting 100+ LLM providers via format conversion.

### Providers Tested
- Ollama (local, free)
- Groq (cloud, free tier - 14,400 req/day)
- Anthropic Claude (via LiteLLM)
- OpenAI GPT (via LiteLLM)

### Format Conversion
LiteLLM automatically converts:
- Anthropic format → OpenAI format
- Anthropic format → Ollama format
- Anthropic format → Groq format

**Benefit**: One bridge server, all providers.

---

## Phase 8: Configuration System

### YAML Configuration
Replaced JSON with YAML for better readability.

**Structure**:
```yaml
proxy:
  port: 29974

kiro:
  exe_path: null  # Auto-detect

kiro_endpoint:  # TRUE=allow, FALSE=block
  telemetry: false
  updates: false
  models: true
  force_toggle_usage_limits: null  # Auto mode

debug:
  debug_mode_enabled: true
  store_interaction_blocks: false

providers:
  kiro:
    enabled: true
    type: passthrough
  
  anthropic:
    enabled: false
    type: anthropic
    api_key: null
    models:
      - name: "claude-3-5-sonnet-20241022"
        alias: ["claude", "sonnet"]

default_model: "kiro-default"
```

### Config Loader (`config_loader.py`)
- Deep merge with hardcoded defaults
- Model name/alias mapping (O(1) lookup)
- Provider management
- Dynamic usage limits logic
- Validation and error handling

---

## Phase 9: Dependency Management

### Requirements Check
Added on-boot dependency checking:
- Reads `_kiropipe/requirements.txt`
- Detects missing packages
- Detects outdated versions
- Offers auto-install option

**User Options**:
1. Auto-install/upgrade all
2. Show manual commands
3. Continue anyway (with warning)

---

## Phase 10: Development Tools Consolidation

### Consolidated Tools
**`analyze_traffic.py`** - Replaces 5 analysis tools:
- Analyzes requests, responses, and pairs
- Decodes binary Event Stream
- Extracts conversation flow

**`test_system.py`** - Replaces 8 testing tools:
- Tests encoder/decoder
- Tests translators
- Tests configuration
- Tests bridge connection
- Tests Ollama connection

### Injection System
**`text_to_stream.py`** - Convert text to AWS Event Stream
**`inject_to_kiro.py`** - Inject messages into Kiro
**`inject_response.py`** - Injection server for testing
**`quick_test.py`** - Quick injection test
**`send_to_kiro.py`** - Send messages to Kiro

### Utilities
**`setup_config.py`** - Interactive configuration wizard
**`find_kiro_pids.py`** - Find Kiro process IDs
**`spawn_and_hook.py`** - Spawn Kiro with custom settings

**Result**: 27 files → 10 files (63% reduction)

---

## Technical Findings

### Port Limitation
mitmproxy ports must be ≤34438.

### Certificate Pinning
Chromium flags override application-level pinning. No binary patching required.

### Streaming Protocol
AWS Q uses streaming similar to Anthropic Claude, indicating shared architecture.

### Tool Use Flow
1. User message → LLM decides to use tool
2. LLM returns tool call (binary)
3. Kiro executes tool locally
4. Kiro sends tool results in next request
5. LLM sees results, responds with final answer

### Conversation History
Every request includes full history (200+ items). This is why requests are 500KB+.

### Tool Format
- Tools wrapped in `toolSpecification` object
- Tool results have content as array: `[{"text": "..."}]`
- Tool calls streamed as JSON chunks

---

## Current Status

### Production Ready
- Traffic interception with certificate bypass
- YAML configuration system
- Multiple provider support (Anthropic, OpenAI, LiteLLM)
- Session tracking and statistics
- Dependency checking with auto-install
- Consolidated development tools

### Tested
- Anthropic Claude (direct API)
- Ollama (local, via LiteLLM)
- Groq (cloud, via LiteLLM)
- Request/response translation
- Tool calling flow
- Multi-turn conversations

### Documentation
- User guides (README, QUICK_START)
- Developer documentation (this journal, devtools README)
- Configuration examples
- Troubleshooting guides

---

## References

### Documentation
- AWS CodeWhisperer API: https://docs.aws.amazon.com/codewhisperer/
- kiro-gateway: https://github.com/jwadow/kiro-gateway
- LiteLLM: https://github.com/BerriAI/litellm
- Ollama: https://ollama.ai

### Tools
- mitmproxy: https://mitmproxy.org/
- FastAPI: https://fastapi.tiangolo.com/
