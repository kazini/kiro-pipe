# Ollama Setup Guide

Complete guide for using KiroPipe with Ollama (100% free, runs locally)

## Why Ollama?

- ✅ **Completely free** - no API keys needed
- ✅ **Runs locally** - your data stays private
- ✅ **No internet required** - works offline
- ✅ **Multiple models** - Llama, Qwen, Mistral, etc.
- ✅ **Easy to use** - simple installation

## Step 1: Install Ollama

### Windows
1. Download from: https://ollama.ai/download
2. Run the installer
3. Ollama will start automatically

### Verify Installation
```bash
ollama --version
```

## Step 2: Pull a Model

### Recommended Models

**For General Use:**
```bash
# Fast and small (2GB)
ollama pull llama3.2:3b

# Better quality (4.7GB)
ollama pull llama3.2:8b
```

**For Coding:**
```bash
# Best for code (4.7GB)
ollama pull qwen2.5-coder:7b

# Smaller coding model (1.9GB)
ollama pull qwen2.5-coder:3b
```

**Check Available Models:**
```bash
ollama list
```

## Step 3: Test Ollama

```bash
ollama run llama3.2
```

Type a message to test. Press Ctrl+D to exit.

## Step 4: Configure KiroPipe

### Create Config File

```bash
copy _kiropipe\kiropipe_config.json.example _kiropipe\kiropipe_config.json
```

### Edit Config

The default config is already set for Ollama! Just verify:

```json
{
  "bridge": {
    "backend": "litellm",
    "model": "ollama/llama3.2",
    "max_tokens": 4096,
    "debug": true
  },
  "litellm": {
    "enabled": true,
    "model": "ollama/llama3.2",
    "api_base": "http://localhost:11434",
    "api_key": null
  }
}
```

**Change Model:**
- For llama3.2:8b → `"model": "ollama/llama3.2:8b"`
- For qwen2.5-coder → `"model": "ollama/qwen2.5-coder:7b"`

## Step 5: Start Bridge Server

```bash
python _kiropipe/engine/bridge_server.py
```

You should see:
```
============================================================
Kiro API Bridge Server
============================================================

Configuration:
  - Backend: litellm
  - Model: ollama/llama3.2
  - Max tokens: 4096
  - Debug mode: True

LiteLLM:
  - Model: ollama/llama3.2
  - API base: http://localhost:11434

Endpoints:
  - POST http://localhost:XXXX/generateAssistantResponse
  - GET  http://localhost:XXXX/health
  - GET  http://localhost:XXXX/config
```

## Step 6: Configure kiropipe.py

Edit `kiropipe.py`:

```python
ENABLE_BRIDGE = True
BRIDGE_URL = 'http://localhost:XXXX'  # Use the port from bridge server
```

## Step 7: Launch Kiro

```bash
python kiropipe.py
```

## Step 8: Test!

1. Open Kiro
2. Send a message
3. You should see a response from your local Ollama model!

## Troubleshooting

### "Connection refused"

**Problem:** Bridge can't connect to Ollama

**Solution:**
```bash
# Check if Ollama is running
ollama list

# If not, start it
ollama serve
```

### "Model not found"

**Problem:** Model not pulled

**Solution:**
```bash
# Pull the model
ollama pull llama3.2

# Verify it's there
ollama list
```

### "Slow responses"

**Problem:** Model is too large for your hardware

**Solution:**
- Use smaller model: `ollama/llama3.2:3b`
- Or use quantized version: `ollama/llama3.2:3b-q4_0`

### "Out of memory"

**Problem:** Not enough RAM

**Solution:**
- Close other applications
- Use smaller model (3b instead of 8b)
- Reduce `max_tokens` in config

## Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| llama3.2:3b | 2GB | Fast | Good | General chat, quick responses |
| llama3.2:8b | 4.7GB | Medium | Better | Detailed responses |
| qwen2.5-coder:3b | 1.9GB | Fast | Good | Code, fast |
| qwen2.5-coder:7b | 4.7GB | Medium | Best | Code, quality |
| llama3.1:70b | 40GB | Slow | Excellent | Best quality (needs powerful PC) |

## Advanced Configuration

### Use Multiple Models

You can switch models without restarting:

1. Stop bridge server (Ctrl+C)
2. Edit config: `"model": "ollama/qwen2.5-coder:7b"`
3. Restart bridge server

### Custom System Prompt

Edit `_kiropipe/engine/request_translator.py` to add custom system prompts.

### Performance Tuning

In config:
```json
{
  "bridge": {
    "max_tokens": 2048  // Lower = faster
  }
}
```

## Free Cloud Alternative: Groq

If you want cloud-based but still free:

1. Get free API key: https://groq.com (14,400 requests/day)
2. Edit config:
```json
{
  "bridge": {
    "backend": "litellm"
  },
  "litellm": {
    "enabled": true,
    "model": "groq/llama-3.1-70b-versatile",
    "api_key": "your-groq-key-here"
  }
}
```

## Next Steps

- Try different models
- Test tool calling
- Experiment with multi-turn conversations
- Compare response quality

## Resources

- Ollama Models: https://ollama.ai/library
- Ollama Docs: https://github.com/ollama/ollama
- LiteLLM Docs: https://docs.litellm.ai/
- KiroPipe Docs: `_kiropipe/SETUP_GUIDE.md`
