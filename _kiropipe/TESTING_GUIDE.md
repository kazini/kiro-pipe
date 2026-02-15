# KiroPipe Testing Guide

Complete guide for testing the KiroPipe system.

## Quick Start

### 1. Test Response Injection (No API Keys Needed)

This tests if Kiro can receive and display synthetic responses.

**Step 1: Start the injection server**
```bash
python _kiropipe/tools/inject_response.py
```

You should see:
```
============================================================
Response Injection Test Server
============================================================

Server running on: http://localhost:8000
Endpoint: POST /generateAssistantResponse
...
```

**Step 2: Configure kiropipe.py**

Edit `kiropipe.py` and set:
```python
ENABLE_BRIDGE = True
BRIDGE_URL = 'http://localhost:8000'
```

**Step 3: Launch Kiro**
```bash
python kiropipe.py
```

**Step 4: Test in Kiro**

Send these messages:
- "Hello, how are you?" → Should get a synthetic text response
- "Please test tool calling" → Should trigger a tool call (readFile)

**Expected Results:**
- Kiro displays the synthetic responses
- Console shows request/response flow
- No errors in either terminal

---

### 2. Test Automated Injection Suite

This verifies the injection server works correctly.

**Step 1: Start injection server** (if not already running)
```bash
python _kiropipe/tools/inject_response.py
```

**Step 2: Run test suite** (in another terminal)
```bash
python _kiropipe/tools/test_injection.py
```

**Expected Output:**
```
============================================================
Test Summary
============================================================
✓ PASS: Simple Response
✓ PASS: Tool Call Response
✓ PASS: Tool Result Response

Total: 3/3 tests passed
============================================================
```

---

### 3. Test Bridge Server (Requires API Keys)

This tests the full bridge with real LLM backends.

**Step 1: Install bridge dependencies**
```bash
pip install -r _kiropipe/bridge_requirements.txt
```

**Step 2: Configure bridge**

Copy and edit config:
```bash
copy _kiropipe\kiropipe_config.json.example _kiropipe\kiropipe_config.json
```

Edit `_kiropipe/kiropipe_config.json`:
```json
{
  "bridge": {
    "backend": "anthropic",
    "model": "claude-3-5-sonnet-20241022",
    "api_key": "your-api-key-here",
    "max_tokens": 4096,
    "debug": true
  }
}
```

**Step 3: Start bridge server**
```bash
python _kiropipe/engine/bridge_server.py
```

**Step 4: Configure kiropipe.py**
```python
ENABLE_BRIDGE = True
BRIDGE_URL = 'http://localhost:8000'
```

**Step 5: Launch Kiro and test**
```bash
python kiropipe.py
```

Send messages in Kiro - they'll be routed through your bridge to the LLM!

---

### 4. Test with Local Models (Free)

Use Ollama for completely free local testing.

**Step 1: Install Ollama**

Download from: https://ollama.ai

**Step 2: Pull a model**
```bash
ollama pull llama3.2:3b
```

**Step 3: Configure bridge for LiteLLM**

Edit `_kiropipe/kiropipe_config.json`:
```json
{
  "bridge": {
    "backend": "litellm",
    "model": "ollama/llama3.2:3b",
    "api_base": "http://localhost:11434",
    "max_tokens": 4096,
    "debug": true
  },
  "litellm": {
    "enabled": true,
    "model": "ollama/llama3.2:3b",
    "api_base": "http://localhost:11434"
  }
}
```

**Step 4: Start bridge and test** (same as step 3 above)

---

## Testing Workflow

### Development Cycle

1. **Capture Real Traffic**
   ```bash
   # Set DEBUG_MODE = True in kiropipe.py
   python kiropipe.py
   # Use Kiro normally
   # Requests saved to _kiropipe/debug_logs/interactions/posted/
   ```

2. **Analyze Captured Requests**
   ```bash
   python _kiropipe/tools/unpack_request.py 19
   # View: _kiropipe/debug_logs/interactions/unpacked/request_19_unpacked.md
   ```

3. **Test Response Generation**
   ```bash
   python _kiropipe/tools/inject_response.py
   # Test with Kiro or automated tests
   ```

4. **Verify Encoding**
   ```bash
   python _kiropipe/tools/test_encoder.py
   ```

5. **Test Bridge**
   ```bash
   python _kiropipe/engine/bridge_server.py
   # Configure kiropipe.py to use bridge
   # Test with Kiro
   ```

---

## Troubleshooting

### Injection Server Issues

**"Address already in use"**
- Another process is using port 8000
- Edit `inject_response.py` and change the port
- Update `BRIDGE_URL` in `kiropipe.py` accordingly

**"Connection refused"**
- Make sure injection server is running
- Check the URL is correct: `http://localhost:8000`
- Verify firewall isn't blocking the connection

**"No response in Kiro"**
- Check console output in both terminals
- Verify `ENABLE_BRIDGE = True` in `kiropipe.py`
- Check `BRIDGE_URL` is correct
- Look for errors in injection server terminal

### Bridge Server Issues

**"API key not configured"**
- Set API key in `_kiropipe/kiropipe_config.json`
- Or set environment variable: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

**"Module not found"**
- Install bridge requirements: `pip install -r _kiropipe/bridge_requirements.txt`

**"Connection timeout"**
- LLM API may be slow or down
- Check your internet connection
- Try increasing timeout in bridge_server.py

**"Invalid response format"**
- Check bridge server console for errors
- Verify the LLM API is returning expected format
- Test with injection server first to isolate the issue

### Kiro Issues

**"Kiro not receiving responses"**
- Check proxy is running (should see mitmproxy output)
- Verify certificate bypass flags are working
- Check `ENABLE_BRIDGE` is `True`
- Look for errors in kiropipe.py console

**"Kiro shows error message"**
- The response format may be incorrect
- Check bridge/injection server console for errors
- Compare with captured real responses
- Test encoding with `test_encoder.py`

---

## Test Scenarios

### Scenario 1: Simple Conversation
**Goal:** Test basic text responses

1. Start injection server
2. Configure and launch Kiro
3. Send: "Hello, how are you?"
4. Verify: Kiro displays synthetic response

### Scenario 2: Tool Calling
**Goal:** Test tool call generation and execution

1. Start injection server
2. Configure and launch Kiro
3. Send: "Please test tool calling"
4. Verify: Kiro shows tool call (readFile)
5. Verify: Tool executes and returns result
6. Verify: Kiro shows final response

### Scenario 3: Real LLM Integration
**Goal:** Test complete bridge with real LLM

1. Configure bridge with API key
2. Start bridge server
3. Configure and launch Kiro
4. Send: "Write a hello world function in Python"
5. Verify: Real LLM response appears in Kiro
6. Test tool calling: "Read the file test.py"
7. Verify: Tool executes and LLM responds

### Scenario 4: Local Model
**Goal:** Test with free local model

1. Install and run Ollama
2. Configure bridge for LiteLLM + Ollama
3. Start bridge server
4. Configure and launch Kiro
5. Send various messages
6. Verify: Local model responses appear in Kiro

---

## Performance Testing

### Response Time
- Injection server: < 100ms
- Bridge + Anthropic: 1-3 seconds
- Bridge + Local (Ollama): 2-5 seconds

### Request Size
- Simple message: ~5KB
- With tools: ~50KB
- With history: 200KB - 1MB+

### Response Size
- Text only: 1-10KB
- With tool calls: 5-20KB
- With usage metrics: +1KB

---

## Validation Checklist

Before deploying:

- [ ] Injection server tests pass
- [ ] Encoder tests pass
- [ ] Bridge server starts without errors
- [ ] Kiro receives and displays responses
- [ ] Tool calls work correctly
- [ ] Tool results are processed
- [ ] Usage metrics are included
- [ ] Error handling works
- [ ] Configuration is documented
- [ ] All dependencies are listed

---

## Next Steps

After testing:

1. **Optimize Performance**
   - Cache conversation history
   - Reduce request size
   - Stream responses faster

2. **Add Features**
   - Multiple LLM backends
   - Fallback logic
   - Cost tracking
   - Response caching

3. **Improve Reliability**
   - Better error handling
   - Retry logic
   - Health checks
   - Monitoring

4. **Documentation**
   - User guide
   - API documentation
   - Configuration examples
   - Troubleshooting guide

---

## Resources

- **Injection Server**: `_kiropipe/tools/inject_response.py`
- **Test Suite**: `_kiropipe/tools/test_injection.py`
- **Bridge Server**: `_kiropipe/engine/bridge_server.py`
- **Configuration**: `_kiropipe/kiropipe_config.json.example`
- **Tools README**: `_kiropipe/tools/README.md`
- **Dev Journal**: `_kiropipe/KIROPIPE_DEV_JOURNAL.md`
