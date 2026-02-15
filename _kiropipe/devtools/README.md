# KiroPipe Development Tools

This directory contains development and testing tools for KiroPipe. These tools are NOT included in releases and are only for developers.

## Tool Categories

### 1. Traffic Analysis
### 2. Testing & Validation
### 3. Message Injection
### 4. Configuration

---

## Traffic Analysis Tools

### `analyze_traffic.py`
**Purpose**: Analyze captured AWS Q traffic (requests and responses)

**What it does**:
- Analyzes request structure and content
- Decodes binary AWS Event Stream responses
- Extracts conversation history, tools, and tool results
- Shows request-response pairs

**Use cases**:
- Understanding AWS Q API format
- Debugging traffic issues
- Analyzing conversation flow
- Extracting tool call patterns

**Usage**:
```bash
# Analyze all interactions in directory
python analyze_traffic.py _kiropipe/debug_logs/interactions

# Analyze single request
python analyze_traffic.py _kiropipe/debug_logs/interactions/posted/request_1.json

# Analyze single response
python analyze_traffic.py _kiropipe/debug_logs/interactions/responses/response_1.bin
```

**Example output**:
```
Request: request_1.json
============================================================
Conversation ID: abc-123
User message: How do I read a file?
History items: 5
Tools available: 15
Tool results: 0

Response: response_1.bin
============================================================
Size: 2048 bytes
Events: 12
Text response (150 chars):
  To read a file, you can use the readFile tool...
```

---

## Testing & Validation Tools

### `test_system.py`
**Purpose**: Test all KiroPipe components

**What it does**:
- Tests event stream encoder/decoder
- Tests request/response translators
- Tests configuration loader
- Tests bridge server connection
- Tests Ollama connection

**Use cases**:
- Verifying installation
- Testing after code changes
- Debugging component issues
- CI/CD integration

**Usage**:
```bash
# Run all tests
python test_system.py

# Run specific test
python test_system.py encoder
python test_system.py translators
python test_system.py config
python test_system.py bridge
python test_system.py ollama
```

**Example output**:
```
============================================================
KiroPipe System Tests
============================================================

Testing Event Stream Encoder
============================================================
Encoded text: 45 bytes
[OK] Text encoding works
[OK] Tool use encoding works

Testing Request/Response Translators
============================================================
[OK] Request translation works
[OK] Response translation works (234 bytes)

[OK] All tests passed!
```

---

### `test_bridge_config.py`
**Purpose**: Test bridge server configuration loading

**What it does**:
- Loads YAML configuration
- Tests model lookup (names and aliases)
- Tests provider configuration
- Tests API base and key extraction
- Tests LiteLLM sub-provider config

**Use cases**:
- Verifying config file syntax
- Testing custom endpoint configuration
- Debugging provider setup
- Validating model aliases

**Usage**:
```bash
python test_bridge_config.py
```

**Example output**:
```
Testing bridge server configuration...

[OK] Config loaded successfully

Testing model lookup:
  ✓ 'kiro-default' -> kiro-default (kiro)
  ✓ 'kiro' -> kiro-default (kiro)
  ✓ 'default' -> kiro-default (kiro)

Testing provider config:
  ✓ kiro:
    Type: passthrough
    API Base: Not set
    API Key: Not set

Testing LiteLLM sub-providers:
  ✓ ollama:
    API Base: http://localhost:11434
    API Key: Not set

[OK] All tests passed!
```

---

### `test_config_robustness.py`
**Purpose**: Test configuration error handling and fallback to defaults

**What it does**:
- Tests valid config loading
- Tests missing config file handling
- Tests broken YAML syntax handling
- Tests empty config file handling
- Tests partial config (missing sections)
- Tests invalid YAML structure
- Tests None config path
- Verifies hardcoded defaults are used as fallback

**Use cases**:
- Verifying error handling
- Testing config validation
- Ensuring graceful degradation
- Validating default values

**Usage**:
```bash
python test_config_robustness.py
```

**Example output**:
```
============================================================
Configuration Robustness Tests
============================================================
Test 1: Valid config file
------------------------------------------------------------
  ✓ Valid config loaded successfully
  ✓ Debug mode is False by default
  ✓ All defaults correct

Test 3: Broken YAML syntax
------------------------------------------------------------
[Config] ERROR: Invalid YAML syntax
[Config]   Line 6, Column 12
[Config]   mapping values are not allowed here
[Config] Using defaults
  ✓ Broken YAML handled gracefully
  ✓ Error message displayed
  ✓ Hardcoded defaults used

============================================================
Results: 7 passed, 0 failed
============================================================

✓ All tests passed!
```

---

### `test_quiet_mode.py`
**Purpose**: Verify quiet mode configuration

**What it does**:
- Checks debug mode setting
- Explains mitmproxy behavior
- Shows how to change debug mode

**Use cases**:
- Verifying quiet mode is working
- Understanding debug mode behavior
- Checking current configuration

**Usage**:
```bash
python test_quiet_mode.py
```

**Example output**:
```
Testing quiet mode configuration...

Debug mode: False

✓ Debug mode DISABLED (quiet mode)
  - mitmproxy will run with -q flag (quiet)
  - Only essential messages will be shown
  - No verbose request/response logging

To change debug mode:
  Edit _kiropipe/kiropipe_config.yaml
  Set debug.debug_mode_enabled: true/false
```

---

## Message Injection Tools

### `text_to_stream.py`
**Purpose**: Convert plain text to AWS Event Stream format

**What it does**:
- Converts text to Anthropic streaming format
- Converts Anthropic format to AWS Event Stream binary
- Simulates word-by-word streaming
- Optionally generates tool calls

**Use cases**:
- Creating test responses
- Simulating LLM responses
- Testing Kiro's response handling
- Debugging format issues

**Usage**:
```bash
# Convert text to stream
python text_to_stream.py "Hello, world!"

# Save to file
python text_to_stream.py "Hello" --output test_response.bin

# Include tool call
python text_to_stream.py "Reading file..." --tool readFile --tool-input '{"path":"test.py"}'
```

**Example output**:
```
Converted text to AWS Event Stream
Size: 156 bytes
Saved to: test_response.bin

Verification:
  Events: 8
  Text: Hello, world!
```

---

### `inject_to_kiro.py`
**Purpose**: Inject messages into Kiro for testing

**What it does**:
- Converts text to AWS Event Stream
- Adds to injection queue
- Queue is automatically processed by kiropipe.py

**Use cases**:
- Testing Kiro's message handling
- Simulating LLM responses without LLM
- Testing tool call flow
- Debugging UI issues

**Usage**:
```bash
# Inject simple message
python inject_to_kiro.py "Hello from injection!"

# Inject with tool call
python inject_to_kiro.py "Reading file..." --tool readFile --tool-input '{"path":"test.py"}'

# Check queue
python inject_to_kiro.py --list
```

**Example output**:
```
Message added to injection queue
Queue position: 1
Total in queue: 1

Next time Kiro requests a response, this message will be injected.
```

**How it works**:
1. Converts text to AWS Event Stream binary
2. Adds to `_kiropipe/debug_logs/.injection_queue.json`
3. kiropipe.py checks queue on each `generateAssistantResponse` request
4. Injects first message from queue
5. Removes injected message from queue

---

### `inject_response.py`
**Purpose**: Run injection server for testing

**What it does**:
- Starts HTTP server on random port
- Accepts injection requests
- Serves injected responses to Kiro

**Use cases**:
- Testing without real LLM
- Rapid prototyping
- UI testing
- Demo mode

**Usage**:
```bash
# Start injection server
python inject_response.py

# In another terminal, send test message
python quick_test.py "Test message"
```

**Example output**:
```
============================================================
Injection Server
============================================================
Port: 54321
Endpoint: http://localhost:54321/generateAssistantResponse

Send requests to inject responses into Kiro
```

---

### `quick_test.py`
**Purpose**: Quick test of injection server

**What it does**:
- Sends test message to injection server
- Shows streaming response
- Verifies format

**Use cases**:
- Testing injection server
- Verifying streaming works
- Quick format checks

**Usage**:
```bash
# Test with message
python quick_test.py "Hello, how are you?"

# Test with tool call
python quick_test.py "Reading file..." --tool
```

---

### `send_to_kiro.py`
**Purpose**: Send messages directly to Kiro (via kiropipe)

**What it does**:
- Sends AWS Q format request to kiropipe
- Receives and displays response
- Shows streaming output

**Use cases**:
- Testing kiropipe without Kiro UI
- Automated testing
- Performance testing

**Usage**:
```bash
# Send message
python send_to_kiro.py "What is 2+2?"

# With conversation ID
python send_to_kiro.py "Follow up question" --conversation-id abc-123
```

---

## Configuration Tools

### `setup_config.py`
**Purpose**: Interactive configuration wizard

**What it does**:
- Guides user through configuration
- Creates `kiropipe_config.yaml`
- Validates settings
- Tests connections

**Use cases**:
- First-time setup
- Switching providers
- Troubleshooting config issues

**Usage**:
```bash
python setup_config.py
```

**Example output**:
```
============================================================
KiroPipe Configuration Setup
============================================================

Choose your LLM backend:
1. Ollama (FREE, local)
2. Groq (FREE, cloud)
3. Anthropic Claude (PAID)
4. OpenAI GPT (PAID)

Enter choice (1-4): 1

Ollama Configuration
------------------------------------------------------------
[OK] Ollama is installed
Available models:
  llama3.2
  qwen2.5-coder:7b

Model name (default: llama3.2): 
[OK] Configuration saved!
```

---

## Utility Tools

### `find_kiro_pids.py`
**Purpose**: Find Kiro process IDs

**What it does**:
- Lists all Kiro.exe processes
- Shows PIDs and window titles
- Identifies main window process

**Use cases**:
- Debugging process issues
- Finding correct PID for monitoring
- Troubleshooting multiple instances

**Usage**:
```bash
python find_kiro_pids.py
```

**Example output**:
```
Kiro Processes:
  PID 12345: Kiro (main window)
  PID 12346: Kiro Helper
  PID 12347: Kiro GPU Process
```

---

### `spawn_and_hook.py`
**Purpose**: Spawn Kiro with custom settings

**What it does**:
- Launches Kiro with specific configuration
- Sets environment variables
- Monitors process

**Use cases**:
- Testing different configurations
- Debugging launch issues
- Development testing

**Usage**:
```bash
python spawn_and_hook.py --port 29974 --debug
```

---

## Tool Organization

### For Release (in `engine/`):
- `bridge_server.py` - Main bridge server
- `config_loader.py` - Configuration management
- `decode_event_stream.py` - Event stream decoder
- `event_stream_encoder.py` - Event stream encoder
- `request_translator.py` - AWS Q → LLM format
- `response_translator.py` - LLM → AWS Event Stream
- `reconstruct_messages.py` - Message reconstruction

### For Development Only (in `devtools/`):
- All tools in this directory
- Not included in releases
- For testing and debugging only

---

## Common Workflows

### 1. Testing New Feature
```bash
# Test components
python test_system.py

# Test with injection
python inject_to_kiro.py "Test message"

# Analyze traffic
python analyze_traffic.py _kiropipe/debug_logs/interactions
```

### 2. Debugging Traffic Issues
```bash
# Capture traffic (enable debug in config)
python kiropipe.py

# Analyze captured traffic
python analyze_traffic.py _kiropipe/debug_logs/interactions

# Test specific request
python send_to_kiro.py "Test message"
```

### 3. Testing Without LLM
```bash
# Start injection server
python inject_response.py

# Send test messages
python quick_test.py "Hello"
python quick_test.py "How are you?"
```

### 4. Setting Up New Provider
```bash
# Run configuration wizard
python setup_config.py

# Test connection
python test_system.py bridge

# Test end-to-end
python send_to_kiro.py "Test message"
```

---

## Development Guidelines

1. **Keep devtools separate**: Don't import devtools in production code
2. **Document new tools**: Add to this README when creating new tools
3. **Consolidate when possible**: Merge similar functionality
4. **Test before committing**: Run `test_system.py` before commits
5. **Clean up**: Remove obsolete tools regularly

---

## Tool Dependencies

All devtools require:
- Python 3.8+
- Packages from `_kiropipe/requirements.txt`
- Access to `_kiropipe/engine/` modules

Some tools require:
- Running bridge server (test_system.py bridge test)
- Running Ollama (test_system.py ollama test)
- Captured traffic (analyze_traffic.py)
- Running kiropipe (inject_to_kiro.py)

---

## Troubleshooting

### "Module not found"
```bash
# Make sure you're in the project root
cd kiro-conduit
python _kiropipe/devtools/tool_name.py
```

### "No such file or directory"
```bash
# Check if debug logs exist
ls _kiropipe/debug_logs/interactions

# Enable debug mode in config
debug:
  debug_mode_enabled: true
  store_interaction_blocks: true
```

### "Connection refused"
```bash
# Check if bridge server is running
python _kiropipe/engine/bridge_server.py

# Check if Ollama is running
ollama list
```

---

## Contributing

When adding new devtools:
1. Follow existing naming conventions
2. Add comprehensive docstring
3. Update this README
4. Add usage examples
5. Test thoroughly

When removing devtools:
1. Check for dependencies
2. Update this README
3. Remove from any scripts that reference it
