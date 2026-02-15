# Quick Start Guide

Get KiroPipe running with a real LLM backend in 5 minutes.

## Option 1: Free Local LLM (Ollama) - Recommended

### Step 1: Install Ollama

**Windows:**
```bash
# Download and install from https://ollama.ai/download
# Or use winget:
winget install Ollama.Ollama
```

### Step 2: Pull a Model

```bash
# Fast and small (2GB)
ollama pull llama3.2

# Or better quality (4.7GB)
ollama pull llama3.2:8b

# Verify it's installed
ollama list
```

### Step 3: Create Config File

```bash
copy _kiropipe\kiropipe_config.json.example _kiropipe\kiropipe_config.json
```

The default config is already set for Ollama - no changes needed!

### Step 4: Test the Bridge

```bash
# Start bridge server (in one terminal)
python _kiropipe/engine/bridge_server.py

# Test it (in another terminal)
python _kiropipe/tools/test_ollama_bridge.py
```

You should see:
```
✓ Ollama is running
✓ Bridge server is running
✓ Request successful
✓ All tests passed!
```

### Step 5: Enable Bridge in kiropipe.py

Edit `kiropipe.py`:

```python
ENABLE_BRIDGE = True
BRIDGE_URL = 'http://localhost:XXXX'  # Use port from bridge server output
```

### Step 6: Launch Kiro

```bash
python kiropipe.py
```

### Step 7: Chat!

Open Kiro and send a message. You should get a response from your local Ollama model!

---

## Option 2: Free Cloud API (Groq)

### Step 1: Get API Key

1. Go to https://groq.com
2. Sign up (free)
3. Get API key (14,400 requests/day free)

### Step 2: Create Config

```bash
copy _kiropipe\kiropipe_config.json.example _kiropipe\kiropipe_config.json
```

Edit `_kiropipe/kiropipe_config.json`:

```json
{
  "bridge": {
    "backend": "litellm",
    "model": "groq/llama-3.1-70b-versatile",
    "max_tokens": 4096,
    "debug": true
  },
  "litellm": {
    "enabled": true,
    "model": "groq/llama-3.1-70b-versatile",
    "api_key": "YOUR_GROQ_API_KEY_HERE"
  }
}
```

### Step 3: Test and Launch

```bash
# Start bridge
python _kiropipe/engine/bridge_server.py

# Enable in kiropipe.py (ENABLE_BRIDGE = True)
# Then launch
python kiropipe.py
```

---

## Troubleshooting

### "Connection refused" to Ollama

```bash
# Check if Ollama is running
ollama list

# If not, start it
ollama serve
```

### "Model not found"

```bash
# Pull the model
ollama pull llama3.2

# Verify
ollama list
```

### Bridge server not starting

```bash
# Install dependencies
pip install -r _kiropipe/bridge_requirements.txt

# Try again
python _kiropipe/engine/bridge_server.py
```

### No response in Kiro

1. Check bridge server is running (should show requests in console)
2. Check `ENABLE_BRIDGE = True` in kiropipe.py
3. Check `BRIDGE_URL` matches bridge server port
4. Check debug logs in `_kiropipe/debug_logs/`

---

## What's Next?

- Try different models: `ollama pull qwen2.5-coder:7b`
- Test tool calling (coming soon)
- Monitor usage: `http://localhost:PORT/stats`
- Read full docs: `_kiropipe/SETUP_GUIDE.md`

---

## Configuration Examples

### Ollama with Different Model

```json
{
  "bridge": {
    "backend": "litellm",
    "model": "ollama/qwen2.5-coder:7b"
  },
  "litellm": {
    "model": "ollama/qwen2.5-coder:7b",
    "api_base": "http://localhost:11434"
  }
}
```

### Anthropic Claude (Paid)

```json
{
  "bridge": {
    "backend": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "sk-ant-your-key-here"
  }
}
```

### OpenAI GPT (Paid)

```json
{
  "bridge": {
    "backend": "openai",
    "model": "gpt-4",
    "api_key": "sk-your-key-here"
  }
}
```

---

## API Endpoints

Once bridge server is running:

- `GET /health` - Server status and stats
- `GET /config` - Current configuration
- `GET /stats` - Detailed usage statistics
- `POST /generateAssistantResponse` - Main API endpoint (used by Kiro)

Example:
```bash
curl http://localhost:PORT/health
curl http://localhost:PORT/stats
```

---

## Performance Tips

### Faster Responses
- Use smaller models: `llama3.2:3b` instead of `llama3.2:8b`
- Reduce `max_tokens` in config
- Use quantized models: `llama3.2:3b-q4_0`

### Better Quality
- Use larger models: `llama3.2:8b` or `qwen2.5-coder:7b`
- Increase `max_tokens` for longer responses
- Try different models for different tasks

### Memory Usage
- Close other applications
- Use smaller models if running out of RAM
- Monitor with Task Manager

---

## Support

- Full setup guide: `_kiropipe/SETUP_GUIDE.md`
- Ollama guide: `_kiropipe/OLLAMA_SETUP.md`
- Architecture: `_kiropipe/BRIDGE_DESIGN.md`
- Issues: Check `_kiropipe/debug_logs/` for error logs
