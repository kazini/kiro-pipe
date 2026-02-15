# KiroPipe

Intercept and redirect Kiro's AWS Q API traffic to custom LLM backends.

## Features

- ✅ **Traffic Interception**: Capture all AWS Q API requests and responses
- ✅ **Telemetry Blocking**: Block telemetry, updates, and usage limits
- ✅ **API Bridge**: Use any LLM backend (Anthropic, OpenAI, Ollama, Groq, etc.)
- ✅ **Format Translation**: Automatic conversion between AWS Q and standard APIs
- ✅ **Streaming Support**: Real-time streaming responses
- ✅ **Tool Calling**: Full support for tool/function calling
- ✅ **Free Options**: Use local models (Ollama) or free cloud tiers (Groq)
- ✅ **No Kiro Modifications**: Works through proxy, Kiro unchanged

## Quick Start

**New to KiroPipe?** See [QUICK_START.md](_kiropipe/QUICK_START.md) for a 5-minute guide!

### Test in 2 Minutes (No API Keys)

```bash
# Terminal 1: Start test server
python _kiropipe/tools/inject_response.py

# Terminal 2: Test it
python _kiropipe/tools/quick_test.py "Hello, how are you?"
```

You should see a synthetic response! This verifies everything works.

### 1. Install

```bash
# Clone or download this repository
cd kiro-conduit

# Install dependencies
pip install -r requirements.txt
pip install -r _kiropipe/bridge_requirements.txt
```

### 2. Basic Usage (Intercept Only)

```bash
python kiropipe.py
```

This launches Kiro with traffic interception and logging.

### 3. Advanced Usage (Custom LLM)

**Step 1**: Configure bridge

```bash
cp _kiropipe/kiropipe_config.json.example _kiropipe/kiropipe_config.json
# Edit kiropipe_config.json with your API keys
```

**Step 2**: Start bridge server

```bash
python _kiropipe/engine/bridge_server.py
```

**Step 3**: Enable bridge in `kiropipe.py`

```python
ENABLE_BRIDGE = True
```

**Step 4**: Run KiroPipe

```bash
python kiropipe.py
```

Now Kiro uses your custom LLM!

## Supported Backends

### Cloud APIs
- **Anthropic Claude** (recommended) - Best quality
- **OpenAI GPT-4** - Good quality
- **Groq** - FREE, very fast (14,400 req/day)

### Local Models (FREE)
- **Ollama** - Run Llama, Qwen, Mistral locally
- **LM Studio** - GUI for local models
- **vLLM** - High-performance inference

### Via LiteLLM (100+ providers)
- Azure OpenAI, Cohere, Hugging Face, Together AI, OpenRouter, and more

## Configuration

### kiropipe.py
```python
DEFAULT_PORT = 29974              # Proxy port
BLOCK_TELEMETRY = True            # Block telemetry
BLOCK_UPDATES = True              # Block updates
DEBUG_MODE = True                 # Enable logging
ENABLE_BRIDGE = False             # Enable API bridge
BRIDGE_URL = 'http://localhost:8000'
```

### kiropipe_config.json
```json
{
  "bridge": {
    "backend": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "your-key"
  }
}
```

## Documentation

- **[Quick Start](_kiropipe/QUICK_START.md)** - Get started in 5 minutes!
- **[Setup Guide](_kiropipe/SETUP_GUIDE.md)** - Complete setup instructions
- **[Testing Guide](_kiropipe/TESTING_GUIDE.md)** - Testing procedures
- **[Tools README](_kiropipe/tools/README.md)** - Development tools
- **[Bridge Design](_kiropipe/BRIDGE_DESIGN.md)** - Architecture and design
- **[Status](_kiropipe/STATUS.md)** - Project status
- **[Changelog](_kiropipe/CHANGELOG.md)** - Version history

## Project Structure

```
kiropipe.py                    # Main launcher
requirements.txt               # Dependencies
_kiropipe/
├── engine/                    # Core functionality
│   ├── bridge_server.py       # FastAPI bridge server
│   ├── request_translator.py  # AWS Q → LLM format
│   ├── response_translator.py # LLM → AWS Event Stream
│   ├── event_stream_encoder.py
│   ├── decode_event_stream.py
│   └── reconstruct_messages.py
├── tools/                     # Development tools
│   ├── test_bridge_server.py
│   └── analyze_interaction_pattern.py
├── debug_logs/                # Captured traffic (DEBUG_MODE)
├── kiropipe_config.json       # Bridge configuration
└── SETUP_GUIDE.md             # Setup instructions
```

## How It Works

```
Kiro
  ↓ AWS Q request
mitmproxy (kiropipe.py)
  ↓ forward to bridge
Bridge Server
  ↓ translate to Anthropic/OpenAI
LLM API
  ↓ streaming response
Bridge Server
  ↓ translate to AWS Event Stream
mitmproxy
  ↓ return to Kiro
Kiro (thinks it's AWS Q)
```

## Free Setup Example

Using Ollama (completely free, runs locally):

```bash
# Install Ollama
# Download from https://ollama.ai

# Pull a model
ollama pull llama3.2:3b

# Configure bridge
{
  "bridge": {"backend": "litellm"},
  "litellm": {
    "enabled": true,
    "model": "ollama/llama3.2",
    "api_base": "http://localhost:11434"
  }
}

# Start bridge
python _kiropipe/engine/bridge_server.py

# Enable bridge in kiropipe.py
ENABLE_BRIDGE = True

# Run
python kiropipe.py
```

## Testing

```bash
# Test bridge components
python _kiropipe/tools/test_bridge_server.py

# Test encoder
python _kiropipe/tools/test_encoder.py

# Analyze captured traffic
python _kiropipe/tools/analyze_interaction_pattern.py
```

## Requirements

- Python 3.8+
- Windows (tested on Windows 11)
- mitmproxy
- psutil
- FastAPI (for bridge)
- Anthropic/OpenAI SDK (optional, for direct API use)
- LiteLLM (optional, for universal LLM support)

## Benefits

1. **Privacy**: Keep data local with Ollama
2. **Cost**: Use free models or free tiers
3. **Flexibility**: Switch models anytime
4. **Transparency**: See all API traffic
5. **Control**: Modify requests/responses
6. **No Lock-in**: Not tied to AWS Q

## Limitations

- Windows only (currently)
- Requires Kiro.exe in specific location
- Bridge adds slight latency
- Some Kiro features may not work with all models

## Troubleshooting

See [SETUP_GUIDE.md](_kiropipe/SETUP_GUIDE.md#troubleshooting) for common issues.

## License

This project is for educational and research purposes.

## Disclaimer

This tool intercepts and modifies network traffic. Use responsibly and in accordance with applicable terms of service.
