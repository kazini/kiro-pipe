# KiroPipe Setup Guide

Complete guide to set up and use KiroPipe with custom LLM backends.

## Quick Start

### 1. Install Dependencies

```bash
# Main dependencies (required)
pip install -r requirements.txt

# Bridge dependencies (required for API bridge)
pip install -r _kiropipe/bridge_requirements.txt
```

### 2. Basic Usage (Intercept Only)

Run KiroPipe to intercept and log AWS Q traffic:

```bash
python kiropipe.py
```

This will:
- Start mitmproxy on port 29974
- Launch Kiro with proxy settings
- Block telemetry and updates
- Log all AWS Q API traffic (if DEBUG_MODE=True)

### 3. Advanced Usage (API Bridge)

Use custom LLM backends instead of AWS Q.

## API Bridge Setup

### Step 1: Configure the Bridge

Copy the example configuration:

```bash
cp _kiropipe/kiropipe_config.json.example _kiropipe/kiropipe_config.json
```

Edit `_kiropipe/kiropipe_config.json`:

```json
{
  "bridge": {
    "backend": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "your-api-key-here",
    "api_base": null,
    "max_tokens": 4096,
    "debug": true
  },
  "litellm": {
    "enabled": false,
    "model": "ollama/llama3.2",
    "api_base": "http://localhost:11434",
    "api_key": null
  }
}
```

### Step 2: Choose Your Backend

#### Option A: Anthropic Claude (Recommended)

1. Get API key from https://console.anthropic.com/
2. Set in config:
   ```json
   {
     "bridge": {
       "backend": "anthropic",
       "model": "claude-3-5-sonnet-20241022",
       "api_key": "sk-ant-..."
     }
   }
   ```

#### Option B: OpenAI

1. Get API key from https://platform.openai.com/
2. Set in config:
   ```json
   {
     "bridge": {
       "backend": "openai",
       "model": "gpt-4",
       "api_key": "sk-..."
     }
   }
   ```

#### Option C: Local Models (Ollama) - FREE

1. Install Ollama from https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull llama3.2:3b      # Fast, 2GB
   ollama pull qwen2.5-coder:7b # Best for code, 4.7GB
   ```
3. Enable LiteLLM in config:
   ```json
   {
     "bridge": {
       "backend": "litellm"
     },
     "litellm": {
       "enabled": true,
       "model": "ollama/llama3.2",
       "api_base": "http://localhost:11434",
       "api_key": null
     }
   }
   ```

#### Option D: Groq (Free Cloud) - FREE

1. Get free API key from https://groq.com (14,400 requests/day)
2. Enable LiteLLM in config:
   ```json
   {
     "bridge": {
       "backend": "litellm"
     },
     "litellm": {
       "enabled": true,
       "model": "groq/llama-3.1-70b-versatile",
       "api_key": "gsk_..."
     }
   }
   ```

### Step 3: Start the Bridge Server

In a separate terminal:

```bash
python _kiropipe/engine/bridge_server.py
```

You should see:
```
============================================================
Kiro API Bridge Server
============================================================

Configuration:
  - Backend: anthropic
  - Model: claude-3-5-sonnet-20241022
  - Max tokens: 4096
  - Debug mode: True

Endpoints:
  - POST http://localhost:8000/generateAssistantResponse
  - GET  http://localhost:8000/health
  - GET  http://localhost:8000/config

============================================================
```

### Step 4: Enable Bridge in KiroPipe

Edit `kiropipe.py` configuration:

```python
# Bridge configuration
ENABLE_BRIDGE = True  # Enable API bridge
BRIDGE_URL = 'http://localhost:8000'  # Bridge server URL
```

### Step 5: Run KiroPipe

```bash
python kiropipe.py
```

Now Kiro will use your custom LLM backend!

## Configuration Reference

### kiropipe.py Settings

```python
DEFAULT_PORT = 29974              # Proxy port (must be ≤34438)
KIRO_EXE_PATH = None              # Custom Kiro.exe path or None
BLOCK_TELEMETRY = True            # Block telemetry
BLOCK_UPDATES = True              # Block update checks
BLOCK_USAGE_LIMITS = False        # Block usage limits display
DEBUG_MODE = True                 # Enable detailed logging
ENABLE_BRIDGE = False             # Enable API bridge
BRIDGE_URL = 'http://localhost:8000'  # Bridge server URL
```

### kiropipe_config.json Settings

```json
{
  "bridge": {
    "backend": "anthropic|openai|litellm",
    "model": "model-name",
    "api_key": "your-key",
    "api_base": "custom-url",
    "max_tokens": 4096,
    "debug": true
  },
  "litellm": {
    "enabled": false,
    "model": "provider/model",
    "api_base": "http://localhost:11434",
    "api_key": null
  }
}
```

## Testing

### Test Bridge Components

```bash
python _kiropipe/tools/test_bridge_server.py
```

### Test Bridge Server

```bash
# Start bridge server
python _kiropipe/engine/bridge_server.py

# In another terminal, check health
curl http://localhost:8000/health

# Check configuration
curl http://localhost:8000/config
```

### Test End-to-End

1. Start bridge server
2. Enable bridge in kiropipe.py
3. Run kiropipe.py
4. Use Kiro AI features
5. Check console output for bridge logs

## Troubleshooting

### Bridge Server Won't Start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install bridge dependencies
```bash
pip install -r _kiropipe/bridge_requirements.txt
```

### Bridge Not Forwarding Requests

**Check**:
1. Is `ENABLE_BRIDGE = True` in kiropipe.py?
2. Is bridge server running on correct port?
3. Check console for `[BRIDGE]` messages

### API Key Errors

**Anthropic**: Set `ANTHROPIC_API_KEY` environment variable or in config
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**OpenAI**: Set `OPENAI_API_KEY` environment variable or in config
```bash
export OPENAI_API_KEY=sk-...
```

### Ollama Connection Failed

**Check**:
1. Is Ollama running? `ollama list`
2. Is model pulled? `ollama pull llama3.2`
3. Is Ollama on correct port? Default: http://localhost:11434

### Kiro Closes Immediately

**Check**:
1. Is another Kiro instance running?
2. Is Kiro.exe in correct location?
3. Check console for error messages

## Advanced Configuration

### Multiple Models

Switch models by editing `kiropipe_config.json` and restarting bridge server.

### Custom System Prompts

Modify `_kiropipe/engine/request_translator.py` to add system prompts.

### Tool Filtering

Modify `_kiropipe/engine/request_translator.py` to filter or modify tools.

### Response Modification

Modify `_kiropipe/engine/response_translator.py` to alter responses.

## Free Model Recommendations

### Local (Best Privacy)
- `ollama/llama3.2:3b` - Fast, good quality, 2GB
- `ollama/qwen2.5-coder:7b` - Best for code, 4.7GB
- `ollama/llama3.2:8b` - Balanced, 4.7GB

### Cloud Free Tier (Best Performance)
- `groq/llama-3.1-70b-versatile` - 14,400 req/day, very fast
- `groq/llama-3.1-8b-instant` - 14,400 req/day, instant

## Architecture

```
Kiro
  ↓ AWS Q request
mitmproxy (kiropipe.py)
  ↓ forward if ENABLE_BRIDGE
Bridge Server (bridge_server.py)
  ↓ translate request
LLM API (Anthropic/OpenAI/Ollama/etc)
  ↓ streaming response
Bridge Server
  ↓ translate to AWS Event Stream
mitmproxy
  ↓ AWS Event Stream
Kiro
```

## Support

For issues or questions:
1. Check console output (DEBUG_MODE=True)
2. Review `_kiropipe/debug_logs/` files
3. Run test suite: `python _kiropipe/tools/test_bridge_server.py`
4. Check BRIDGE_DESIGN.md for architecture details
