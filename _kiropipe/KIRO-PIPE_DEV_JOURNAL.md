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

## Phase 11: Custom Endpoint Support

### Problem
Users needed to use custom API endpoints:
- OpenRouter (OpenAI-compatible aggregator)
- Together AI (OpenAI-compatible)
- Custom proxies and deployments
- Self-hosted API servers

### Solution
Added `api_base` field to ALL providers in configuration.

**Configuration Structure**:
```yaml
providers:
  anthropic:
    api_base: "https://api.anthropic.com"  # Or custom proxy
    api_key: null
  
  litellm:
    ollama:
      api_base: "http://localhost:11434"
    groq:
      api_base: "https://api.groq.com/openai/v1"
    openai:
      api_base: "https://api.openai.com/v1"  # Or OpenRouter
    openrouter:
      api_base: "https://openrouter.ai/api/v1"
```

### Implementation
**Config Loader Updates**:
- `get_api_base(provider, sub_provider)` - Extract endpoint URL
- `get_api_key(provider, sub_provider)` - Extract API key
- Support for nested sub-providers (LiteLLM)

**Bridge Server Updates**:
- Removed hardcoded `BRIDGE_CONFIG` and `LITELLM_CONFIG`
- Load config via `config_loader.load_config()`
- Pass `api_base` and `api_key` to API clients
- Dynamic provider/model selection from config

**API Client Updates**:
- `call_anthropic_api()` - Accepts `api_base` parameter
- `call_openai_api()` - Accepts `api_base` parameter
- `call_litellm_api()` - Accepts `api_base` parameter
- All clients use custom endpoints when provided

### Benefits
- Use any OpenAI-compatible API (OpenRouter, Together AI, etc.)
- Custom Anthropic proxies and deployments
- Self-hosted models with compatible APIs
- No code changes needed - just config

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


---

## Phase 12: Model List Discovery & Testing

### Problem
Unknown whether Kiro uses:
- **Hardcoded model list** - Models embedded in binary, cannot add new ones
- **Dynamic model list** - Models fetched via API, can inject custom models

This affects our strategy:
- **If hardcoded**: Must replace existing models when selected (model swapping)
- **If dynamic**: Can inject custom models into the list (model addition)

### Investigation Approach

**Step 1: Endpoint Discovery**
Monitor all AWS Q API calls to find model-related endpoints:
- Look for paths containing: `model`, `list`, `available`, `configuration`
- Check authentication responses for embedded model lists
- Analyze Kiro's resources folder for model configs

**Step 2: Response Injection Testing**
Created `test_model_injection.py` to generate fake model list responses:
- Multiple event types: `modelListEvent`, `availableModelsEvent`, `configurationEvent`
- Multiple payload formats: simple list, with metadata, nested structure
- Fake models: "Custom Test Model 1", "Custom Test Model 2"

**Step 3: Observation**
Inject fake responses and observe:
- Do fake models appear in Kiro's model selection UI?
- Does Kiro make API calls to fetch models?
- Are models loaded from local files?

### Testing Tools Created

**`discover_endpoints.py`**
- Analyzes captured traffic for model-related endpoints
- Identifies API call patterns
- Reports discovered endpoints with call counts

**`test_model_injection.py`**
- Generates fake model list responses in AWS Event Stream format
- Creates multiple test variations (event types × payload formats)
- Saves test binaries for manual injection
- Provides detailed testing instructions

### Expected Outcomes

**Scenario A: Dynamic Model List**
- Fake models appear in UI
- We can inject custom models via API
- Strategy: Add our models to the list, let user select them
- Implementation: Intercept model list endpoint, append custom models

**Scenario B: Hardcoded Model List**
- Fake models don't appear in UI
- Models are embedded in binary or local config
- Strategy: Intercept model selection, swap backend transparently
- Implementation: When user selects "Claude Sonnet", route to our custom model

### Usage Limits Toggle Strategy

Related issue: Usage limits should only be blocked when using custom models.

**Current Behavior**:
- `force_toggle_usage_limits` is static (always on/off/auto)
- Doesn't adapt to which model is being used

**Desired Behavior**:
- When Kiro model selected → Allow usage limits (let AWS track usage)
- When custom model selected → Block usage limits (we're not using AWS)

**Implementation Plan**:
1. Track current model in `KiroInterceptor.current_model`
2. Detect model switches from request body
3. Dynamically toggle usage limits based on model type:
   ```python
   if current_model == 'kiro-default':
       # Allow usage limits - using AWS
       allow_usage_limits = True
   else:
       # Block usage limits - using custom provider
       allow_usage_limits = False
   ```

### Current Status
- ⏳ Awaiting endpoint discovery results
- ⏳ Awaiting injection test results
- 📝 Tools created and ready for testing
- 📋 Instructions documented

### Next Steps
1. Run `discover_endpoints.py` while using Kiro
2. Look for model-related API calls
3. If found: Test injection with fake models
4. If not found: Search local resources for model configs
5. Document findings and implement appropriate strategy
6. Implement dynamic usage limits toggle



### Discovery Results

**Endpoint Found:** `/ListAvailableModels`
- Full path: `/ListAvailableModels?origin=AI_EDITOR&profileArn=...`
- Method: GET
- Host: `q.us-east-1.amazonaws.com`

**Conclusion:** Kiro DOES fetch models dynamically via API!

### Implementation: Model Injection Test

Added experimental code to `kiropipe.py` to inject a fake model:

**Request Interception (line ~231):**
- Detects `ListAvailableModels` requests
- Logs interception for visibility

**Response Modification (line ~497):**
- Parses JSON response
- Injects fake model: "🧪 TEST Custom Model"
- Updates response with modified list
- Logs success/failure

**Fake Model Structure:**
```python
{
    "id": "test-custom-model-1",
    "name": "🧪 TEST Custom Model",
    "description": "Fake model to test dynamic loading",
    "provider": "kiropipe-test",
    "capabilities": ["chat", "tools"],
    "status": "available"
}
```

### Testing Status
- ⏳ Awaiting test results
- ⏳ Need to verify if fake model appears in Kiro UI
- ⏳ Need to confirm actual response format (JSON vs Event Stream)

### Next Steps
1. Restart kiropipe.py with injection code
2. Open Kiro and check model selector
3. Look for "🧪 TEST Custom Model" in the list
4. If visible: SUCCESS - we can add custom models!
5. If not visible: Check response format and adjust injection code



### ✅ TEST RESULTS: SUCCESS!

**Conclusion:** Kiro has a DYNAMIC model list fetched via API!

**Evidence:**
- Fake model "🧪 TEST Custom Model" appeared in Kiro's UI
- Model list is fetched from `/ListAvailableModels` endpoint
- Response format is JSON (not AWS Event Stream)
- Structure captured in `original_models.json`

**Model Format Discovered:**
```json
{
  "modelId": "unique-id",
  "modelName": "Display Name",
  "description": "Description text",
  "promptCaching": {...},
  "rateMultiplier": 1.0,
  "rateUnit": "Credit",
  "supportedInputTypes": ["TEXT", "IMAGE"],
  "tokenLimits": {
    "maxInputTokens": 200000,
    "maxOutputTokens": null
  }
}
```

**What This Enables:**
1. ✅ Can inject custom models into Kiro's UI
2. ✅ Users can select custom models from dropdown
3. ✅ No need to replace existing models
4. ✅ Clean integration with Kiro's interface

### Implementation Strategy: Model Addition

Since Kiro has dynamic models, we'll use the **Model Addition** strategy:

**Step 1: Inject Custom Models** (DONE)
- Intercept `/ListAvailableModels` response
- Parse JSON response
- Add custom models from config
- Match exact format from Kiro's models

**Step 2: Detect Model Selection** (NEXT)
- Parse `generateAssistantResponse` requests
- Extract `modelId` from request body
- Track current model in interceptor state

**Step 3: Route to Custom Backend**
- Check if selected model is custom
- If custom: route to bridge server
- If Kiro: pass through to AWS Q

**Step 4: Dynamic Usage Limits**
- Track if current model is Kiro or custom
- Block usage limits when using custom models
- Allow usage limits when using Kiro models

### Current Status
- ✅ Endpoint discovered
- ✅ Format understood
- ✅ Test injection successful
- ✅ Dynamic loading confirmed
- ⏳ Config integration pending
- ⏳ Model selection detection pending
- ⏳ Usage limits toggle pending



### ✅ IMPLEMENTATION COMPLETE!

**Status:** All features implemented and integrated

**Changes Made:**

1. **Model Tracking** (Line ~220)
   - Added `self.kiro_model_ids` - Tracks Kiro's original models
   - Added `self.custom_model_ids` - Tracks injected custom models
   - Added `self.model_is_kiro` - Boolean flag for current model type

2. **Model Injection** (Line ~503)
   - Fetches Kiro's models dynamically from `/ListAvailableModels`
   - Tracks all Kiro model IDs
   - Injects models from config (all enabled providers except 'kiro')
   - Injects dummy test models from `devtools/dummy_models.json` (debug mode only)
   - Matches exact format from Kiro's models
   - All debug messages wrapped in `if DEBUG_MODE_ENABLED:`

3. **Model Selection Detection** (Line ~420)
   - Parses `generateAssistantResponse` requests
   - Extracts `modelId` from request body
   - Updates `self.current_model` and `self.model_is_kiro`
   - Logs model selection (debug mode only)

4. **Dynamic Usage Limits** (Line ~257)
   - Simplified to use `self.model_is_kiro` flag
   - Blocks usage limits only for custom models
   - Allows usage limits for Kiro models
   - Automatic toggle based on model selection

5. **Debug Messages** (Various)
   - Model-related endpoint detection: debug-only
   - Model injection messages: debug-only
   - Model selection messages: debug-only
   - Clean output when debug mode is off

6. **Dummy Test Models** (NEW)
   - Created `_kiropipe/devtools/dummy_models.json`
   - Contains 2 test models for debugging
   - Only loaded when `DEBUG_MODE_ENABLED = True`
   - Graceful error handling:
     - Silent if file doesn't exist
     - Single-line warning if file exists but invalid
     - Validates required fields (modelId, modelName)

**Integration:**
- ✅ Works with existing model routing code
- ✅ Works with existing bridge server
- ✅ Works with existing config system
- ✅ Works with existing injection queue

**Testing:**
- ✅ Tested with fake model injection
- ✅ Confirmed dynamic model loading
- ✅ Captured Kiro's model format
- ⏳ Pending: Test with real config models
- ⏳ Pending: Test model selection detection
- ⏳ Pending: Test usage limits toggle
- ⏳ Pending: Test dummy models in debug mode

