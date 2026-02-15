# KiroPipe

Intercept Kiro's AWS Q API traffic and redirect to custom LLM backends.

## What It Does

- Intercepts Kiro's network traffic via proxy
- Translates AWS Q format to standard LLM APIs
- Supports Anthropic, OpenAI, Ollama, Groq, and 100+ providers
- Works without modifying Kiro binaries
- Runs local models or cloud APIs

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with Kiro's default models
python kiropipe.py

# Configure custom LLM (optional)
cp _kiropipe/kiropipe_config.yaml.example _kiropipe/kiropipe_config.yaml
# Edit config, then run again
```

## Features

- **Multiple Providers**: Anthropic, OpenAI, Ollama, Groq, 100+ via LiteLLM
- **Model Aliases**: Use short names like "claude" or "llama"
- **Session Tracking**: Monitor usage per conversation
- **Auto-Install**: Checks and installs missing dependencies
- **Debug Mode**: Capture and analyze traffic
- **Free Options**: Ollama (local) or Groq (cloud, 14k req/day)

## Configuration

Edit `_kiropipe/kiropipe_config.yaml`:

```yaml
# Use Kiro's default models (no changes needed)
default_model: "kiro-default"

# Or use Anthropic Claude
providers:
  anthropic:
    enabled: true
    api_key: "your-key"
    models:
      - name: "claude-3-5-sonnet-20241022"
        alias: ["claude"]

default_model: "claude"

# Or use local Ollama
providers:
  litellm:
    enabled: true
    ollama:
      api_base: "http://localhost:11434"
      models:
        - name: "ollama/llama3.2"
          alias: ["llama"]

default_model: "llama"
```

## Directory Structure

```
_kiropipe/
├── engine/              # Core functionality
│   ├── bridge_server.py         # API bridge server
│   ├── config_loader.py         # Configuration management
│   ├── decode_event_stream.py   # AWS Event Stream decoder
│   ├── event_stream_encoder.py  # AWS Event Stream encoder
│   ├── request_translator.py    # AWS Q → LLM format
│   ├── response_translator.py   # LLM → AWS Event Stream
│   └── requirements.txt         # Dependencies
│
├── devtools/            # Development tools (not in releases)
│   ├── analyze_traffic.py       # Traffic analyzer
│   ├── test_system.py           # System tester
│   ├── inject_to_kiro.py        # Message injection
│   └── README.md                # Tool documentation
│
├── debug_logs/          # Debug output (when enabled)
│   └── interactions/
│       ├── posted/      # Captured requests
│       └── responses/   # Captured responses
│
├── kiropipe_config.yaml         # Configuration file
├── KIROPIPE_DEV_JOURNAL.md      # Development history
└── README.md                    # This file
```

## How It Works

```
User → Kiro → kiropipe.py (proxy) → Bridge Server → LLM API
                                         ↓
                                    Translates formats
                                         ↓
                                    AWS Event Stream
                                         ↓
                                    Back to Kiro
```

1. Kiro sends AWS Q format request
2. Proxy intercepts and forwards to bridge
3. Bridge translates to LLM format (Anthropic/OpenAI)
4. LLM responds with streaming data
5. Bridge translates back to AWS Event Stream binary
6. Kiro receives and displays response

## Supported Backends

### Direct APIs
- **Anthropic Claude** - Primary supported mode
- **OpenAI GPT** - Direct API support

### Via LiteLLM (100+ providers)
- **Ollama** - Local models (free)
- **Groq** - Cloud, free tier (14,400 req/day)
- **Together AI** - Cloud with free credits
- **OpenRouter** - Access to multiple models
- And 100+ more providers

## Free Options

### Local (No API Key)
- Ollama + Llama 3.2 (2-8GB models)
- Ollama + Qwen 2.5 Coder (coding-focused)
- LM Studio

### Cloud (Free Tier)
- Groq (14,400 requests/day)
- Together AI (free credits)
- OpenRouter (free models)

## Configuration Options

### Proxy Settings
```yaml
proxy:
  port: 29974  # Proxy port

kiro:
  exe_path: null  # Auto-detect or custom path
```

### Kiro Endpoint Control
```yaml
kiro_endpoint:  # TRUE=allow, FALSE=block
  telemetry: false  # Block telemetry
  updates: false    # Block updates
  models: true      # Allow Kiro models
  force_toggle_usage_limits: null  # Auto mode
```

### Debug Settings
```yaml
debug:
  debug_mode_enabled: true          # Console logging
  store_interaction_blocks: false   # Save to files
```

## API Endpoints

When bridge server is running:

- `POST /generateAssistantResponse` - Main API (mimics AWS Q)
- `GET /health` - Server status + statistics
- `GET /config` - Current configuration
- `GET /stats` - Detailed usage per session

## Development

### Run Tests
```bash
python _kiropipe/devtools/test_system.py
```

### Analyze Traffic
```bash
python _kiropipe/devtools/analyze_traffic.py _kiropipe/debug_logs/interactions
```

### Inject Test Messages
```bash
python _kiropipe/devtools/inject_to_kiro.py "Test message"
```

See `_kiropipe/devtools/README.md` for all development tools.

## Troubleshooting

### Dependencies Missing
```bash
# Auto-install when prompted, or manually:
pip install -r _kiropipe/requirements.txt
```

### Ollama Connection Failed
```bash
# Check if Ollama is running
ollama list

# Start if needed
ollama serve
```

### No Response in Kiro
1. Check bridge server is running
2. Verify config has correct model enabled
3. Check debug logs in `_kiropipe/debug_logs/`

## Documentation

- **KIROPIPE_DEV_JOURNAL.md** - Development history and technical details
- **devtools/README.md** - Development tools documentation
- **kiropipe_config.yaml.example** - Configuration examples

## Requirements

- Python 3.8+
- Windows (tested on Windows 11)
- mitmproxy
- psutil
- httpx
- pyyaml
- FastAPI (for bridge server)
- LiteLLM (optional, for universal LLM support)

## License

Educational and research purposes.

## Disclaimer

This tool intercepts and modifies network traffic. Use responsibly and in accordance with applicable terms of service.
