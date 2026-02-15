# Kiro API Bridge Design

## Overview
Create a local server that translates between AWS Q API format and standard LLM APIs (Anthropic Claude, OpenAI, local models).

## Response Format Analysis

### AWS Q Response Structure
**Format**: AWS Event Stream (binary streaming protocol)

**Event Types**:
1. `assistantResponseEvent` - Text content chunks
   ```json
   {"content": "text chunk"}
   ```

2. `toolUseEvent` - Tool call chunks (streamed)
   ```json
   {
     "name": "readFile",
     "toolUseId": "tooluse_xxx",
     "input": "partial json string"
   }
   ```

3. `meteringEvent` - Usage tracking
   ```json
   {
     "unit": "credit",
     "unitPlural": "credits",
     "usage": 0.214
   }
   ```

4. `contextUsageEvent` - Context window usage
   ```json
   {"contextUsagePercentage": 53.54}
   ```

### Request Format
```json
{
  "conversationState": {
    "conversationId": "uuid",
    "agentContinuationId": "uuid",
    "agentTaskType": "vibe",
    "chatTriggerType": "MANUAL",
    "history": [
      {
        "userInputMessage": {
          "content": "system prompt and instructions...",
          "modelId": "auto"
        }
      },
      {
        "userInputMessage": {
          "content": "previous user message",
          "modelId": "auto"
        }
      },
      {
        "assistantResponseMessage": {
          "content": "previous assistant response"
        }
      }
      // ... all previous turns
    ],
    "currentMessage": {
      "userInputMessage": {
        "content": "current user message",
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

**Important**: 
- `history` array contains ALL previous messages (can be 200+ items)
- First message is usually system prompt with identity and instructions
- Requests can be 500KB+ due to full conversation history
- History includes both user and assistant messages

## Target API Format

### Primary: Anthropic Claude API
**Why**: AWS Q is clearly based on Claude
- Similar tool use format
- Streaming event structure matches
- Native support for tool calling

**Anthropic Messages API**:
```json
POST /v1/messages
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 4096,
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "tools": [...],
  "stream": true
}
```

**Response (streaming)**:
```
event: message_start
data: {"type":"message_start","message":{...}}

event: content_block_delta
data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}

event: message_delta
data: {"type":"message_delta","usage":{...}}
```

### Secondary: OpenAI API
**For compatibility with OpenAI clients**

```json
POST /v1/chat/completions
{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "tools": [...],
  "stream": true
}
```

## Bridge Architecture

### Components

1. **Proxy Server** (mitmproxy addon)
   - Intercepts AWS Q requests
   - Forwards to local bridge server
   - Returns AWS Event Stream responses

2. **Bridge Server** (FastAPI/Flask)
   - Receives AWS Q format requests
   - Translates to target API format
   - Calls backend LLM (Anthropic/OpenAI/local)
   - Translates response back to AWS Event Stream
   - Returns to proxy

3. **Format Converters**
   - AWS Q → Anthropic
   - Anthropic → AWS Q Event Stream
   - AWS Q → OpenAI (optional)
   - OpenAI → AWS Q Event Stream (optional)

### Data Flow

```
Kiro
  ↓ (AWS Q request)
Proxy (mitmproxy)
  ↓ (forward)
Bridge Server
  ↓ (translate to Anthropic)
Anthropic API / OpenAI API / Local LLM
  ↓ (streaming response)
Bridge Server
  ↓ (translate to AWS Event Stream)
Proxy
  ↓ (AWS Event Stream)
Kiro
```

## Implementation Plan

### Phase 1: Event Stream Encoder ✅ COMPLETE
Create AWS Event Stream encoder to generate binary responses

**Status**: Implemented and tested
**Location**: `_kiropipe/engine/event_stream_encoder.py`

### Phase 2: Request Translator ✅ COMPLETE
Convert AWS Q requests to Anthropic/OpenAI format

**Status**: Implemented and tested
**Location**: `_kiropipe/engine/request_translator.py`

### Phase 3: Response Translator ✅ COMPLETE
Convert Anthropic/OpenAI streaming responses to AWS Event Stream

**Status**: Implemented and tested
**Location**: `_kiropipe/engine/response_translator.py`

### Phase 4: Bridge Server ✅ COMPLETE
FastAPI server that:
1. Receives AWS Q requests on `/generateAssistantResponse`
2. Translates to Anthropic/OpenAI format
3. Calls LLM API (Anthropic/OpenAI/LiteLLM)
4. Streams response back as AWS Event Stream

**Status**: Implemented
**Location**: `_kiropipe/engine/bridge_server.py`

**Endpoints**:
- `POST /generateAssistantResponse` - Main API endpoint
- `GET /health` - Health check
- `GET /config` - View configuration

### Phase 5: Proxy Integration ⏳ NEXT
Update mitmproxy addon to:
1. Intercept `/generateAssistantResponse` requests
2. Forward to local bridge server (e.g., `http://localhost:8000`)
3. Return bridge server response to Kiro

**Status**: Not started
**Location**: `kiropipe.py` (update KiroInterceptor class)

## Configuration

```python
# Bridge configuration with LiteLLM support
BRIDGE_CONFIG = {
    # Backend selection
    'use_litellm': True,  # Use LiteLLM for universal compatibility
    
    # LiteLLM configuration (supports 100+ providers)
    'litellm': {
        'model': 'ollama/llama3.2',  # Format: provider/model
        # Examples:
        # 'openai/gpt-4'
        # 'anthropic/claude-3-5-sonnet-20241022'
        # 'ollama/qwen2.5-coder'
        # 'groq/llama-3.1-70b'
        'api_base': 'http://localhost:11434',  # For local models
        'api_key': None,  # Not needed for local models
    },
    
    # Direct API configuration (if not using LiteLLM)
    'direct': {
        'backend': 'anthropic',  # or 'openai', 'local'
        'api_key': 'your-api-key',
        'model': 'claude-3-5-sonnet-20241022',
        'base_url': 'https://api.anthropic.com',
        'max_tokens': 4096,
    }
}

# Free model recommendations
FREE_MODELS = {
    'local_fast': 'ollama/llama3.2:3b',  # Fast, good quality
    'local_coding': 'ollama/qwen2.5-coder:7b',  # Best for code
    'local_balanced': 'ollama/llama3.2:8b',  # Balanced
    'cloud_fast': 'groq/llama-3.1-70b-versatile',  # Free tier, very fast
    'cloud_coding': 'groq/llama-3.1-8b-instant',  # Free, instant
}
```

## LiteLLM Integration

### Installation
```bash
pip install litellm
```

### Usage in Bridge
```python
from litellm import completion

def call_llm(messages, tools=None, stream=True):
    """Universal LLM caller using LiteLLM"""
    response = completion(
        model=BRIDGE_CONFIG['litellm']['model'],
        messages=messages,
        tools=tools,
        stream=stream,
        api_base=BRIDGE_CONFIG['litellm']['api_base'],
        api_key=BRIDGE_CONFIG['litellm']['api_key']
    )
    return response
```

### Supported Providers (via LiteLLM)
- **OpenAI**: gpt-4, gpt-3.5-turbo
- **Anthropic**: claude-3-opus, claude-3-sonnet
- **Ollama**: Any local model
- **Groq**: llama3, mixtral (free tier)
- **Azure OpenAI**: All Azure models
- **Cohere**: command, command-light
- **Hugging Face**: Any HF model
- **Together AI**: 50+ open source models
- **OpenRouter**: 100+ models aggregated
- **Local**: vLLM, text-generation-webui, LM Studio

### Benefits
1. **Single interface** for all providers
2. **Automatic format conversion** (OpenAI ↔ Anthropic ↔ others)
3. **Streaming support** for all providers
4. **Tool calling** standardized across providers
5. **Fallback logic** (try multiple providers)
6. **Cost tracking** built-in
7. **MIT license** - can bundle freely

## Benefits

1. **Use any LLM**: Anthropic, OpenAI, local models (Ollama, LM Studio), 100+ providers via LiteLLM
2. **Free options**: Local models (Ollama) or free cloud tiers (Groq, Together AI)
3. **No Kiro modifications**: Works through proxy
4. **Transparent**: Kiro thinks it's talking to AWS Q
5. **Flexible**: Easy to switch backends via config
6. **Cost control**: Use cheaper/free models
7. **Privacy**: Keep data local with local models
8. **Universal compatibility**: LiteLLM handles format conversion automatically

## Recommended Free Setup

### Option 1: Local (Best Privacy)
```bash
# Install Ollama
# Download from https://ollama.ai

# Pull a model
ollama pull llama3.2:3b  # Fast, 2GB
# or
ollama pull qwen2.5-coder:7b  # Better for code, 4.7GB

# Ollama runs on http://localhost:11434
```

### Option 2: Cloud Free Tier (Best Performance)
```bash
# Get free API key from https://groq.com
# 14,400 requests/day free
# Very fast inference

# Configure in bridge:
model: 'groq/llama-3.1-70b-versatile'
api_key: 'your-groq-key'
```

## Next Steps

1. Implement AWS Event Stream encoder
2. Test encoding/decoding round-trip
3. Build request translator (AWS Q → Anthropic)
4. Build response translator (Anthropic → AWS Q)
5. Create bridge server
6. Integrate with proxy
7. Test with Kiro

## Native AWS Event Stream Support

**Python libraries**:
- `awscrt` - AWS Common Runtime (official)
- Can encode/decode event-stream natively
- Used by AWS SDKs

**Alternative**: Manual implementation (what we're doing)
- Full control over format
- No external dependencies
- Educational value

**Recommendation**: Start with manual implementation, optimize later if needed.
