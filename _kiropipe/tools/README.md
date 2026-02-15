# KiroPipe Tools

Development and testing tools for the KiroPipe project.

## Analysis Tools

### unpack_request.py
Unpacks captured AWS Q requests into readable JSON and Markdown formats.

**Usage:**
```bash
python _kiropipe/tools/unpack_request.py <request_number>
```

**Example:**
```bash
python _kiropipe/tools/unpack_request.py 19
```

**Output:**
- `_kiropipe/debug_logs/interactions/unpacked/request_19_unpacked.json` - Organized JSON
- `_kiropipe/debug_logs/interactions/unpacked/request_19_unpacked.md` - Readable Markdown

**Features:**
- Extracts conversation history (all previous messages)
- Shows tool definitions and tool results
- Displays metadata and statistics
- Formats for easy reading

---

### inspect_request_structure.py
Deep analysis of request structure and format.

**Usage:**
```bash
python _kiropipe/tools/inspect_request_structure.py
```

**Output:**
- Analyzes the latest request
- Shows structure breakdown
- Identifies patterns

---

### analyze_interaction_pattern.py
Analyzes request/response patterns to understand the conversation flow.

**Usage:**
```bash
python _kiropipe/tools/analyze_interaction_pattern.py
```

**Output:**
- Shows request-response pairs
- Identifies tool call patterns
- Displays conversation flow

---

## Testing Tools

### inject_response.py
HTTP server that injects synthetic AWS Event Stream responses for testing.

**Usage:**
```bash
python _kiropipe/tools/inject_response.py
```

**Server:** `http://localhost:8000`

**Integration with Kiro:**
1. Edit `kiropipe.py`:
   ```python
   ENABLE_BRIDGE = True
   BRIDGE_URL = 'http://localhost:8000'
   ```
2. Run `kiropipe.py` to launch Kiro
3. Send messages in Kiro to test

**Test Scenarios:**
- Normal message: "Hello, how are you?"
- Tool call test: "Please test tool calling"
- Tool results are automatically detected

**Features:**
- Generates valid AWS Event Stream responses
- Simulates text responses
- Simulates tool calls
- Includes usage metrics

---

### test_injection.py
Automated test suite for the injection server.

**Usage:**
```bash
# Start injection server first
python _kiropipe/tools/inject_response.py

# In another terminal, run tests
python _kiropipe/tools/test_injection.py
```

**Tests:**
1. Simple text response
2. Tool call response
3. Tool result response

**Output:**
- Decodes responses
- Reconstructs messages
- Displays content
- Shows pass/fail status

---

### quick_test.py
Quick test with custom message - send any text and see the response.

**Usage:**
```bash
python _kiropipe/tools/quick_test.py "Your message here" [url]
```

**Examples:**
```bash
# Test with injection server
python _kiropipe/tools/quick_test.py "Hello, how are you?"

# Test tool calling
python _kiropipe/tools/quick_test.py "Please test tool calling"

# Test with custom URL
python _kiropipe/tools/quick_test.py "Hello" http://localhost:8000
```

**Features:**
- Send custom messages
- Displays decoded response
- Shows tool calls if any
- Shows usage metrics
- Works with injection or bridge server

**Default URL:** `http://localhost:8000`

---

### test_encoder.py
Tests the AWS Event Stream encoder/decoder round-trip.

**Usage:**
```bash
python _kiropipe/tools/test_encoder.py
```

**Tests:**
- Text chunk encoding
- Tool use encoding
- Metering events
- Context usage events
- Round-trip encoding/decoding

---

## Workflow Examples

### Analyzing Captured Traffic

1. **Capture traffic** by using Kiro with `kiropipe.py` running
2. **List captured requests:**
   ```bash
   dir _kiropipe\debug_logs\interactions\posted
   ```
3. **Unpack a request:**
   ```bash
   python _kiropipe/tools/unpack_request.py 19
   ```
4. **View the unpacked files:**
   - JSON: `_kiropipe/debug_logs/interactions/unpacked/request_19_unpacked.json`
   - Markdown: `_kiropipe/debug_logs/interactions/unpacked/request_19_unpacked.md`

### Testing Response Generation

1. **Start injection server:**
   ```bash
   python _kiropipe/tools/inject_response.py
   ```
2. **Run automated tests:**
   ```bash
   python _kiropipe/tools/test_injection.py
   ```
3. **Test with Kiro:**
   - Edit `kiropipe.py` to enable bridge
   - Launch Kiro via `kiropipe.py`
   - Send test messages

### Developing the Bridge

1. **Test encoder:**
   ```bash
   python _kiropipe/tools/test_encoder.py
   ```
2. **Test injection server:**
   ```bash
   python _kiropipe/tools/test_injection.py
   ```
3. **Analyze real requests:**
   ```bash
   python _kiropipe/tools/unpack_request.py <number>
   ```
4. **Compare formats** to ensure compatibility

---

## Requirements

All tools require the dependencies in `requirements.txt`:
```bash
pip install -r requirements.txt
```

For bridge testing, also install:
```bash
pip install -r _kiropipe/bridge_requirements.txt
```

---

## Directory Structure

```
_kiropipe/tools/
├── README.md                          # This file
├── unpack_request.py                  # Request unpacker
├── inspect_request_structure.py       # Structure analyzer
├── analyze_interaction_pattern.py     # Pattern analyzer
├── inject_response.py                 # Response injection server
├── test_injection.py                  # Injection test suite
└── test_encoder.py                    # Encoder test suite
```

---

## Tips

- **Debug Mode**: Enable `DEBUG_MODE = True` in `kiropipe.py` to capture all traffic
- **Request Numbers**: Check `_kiropipe/debug_logs/interactions/posted/` for available requests
- **Port Conflicts**: If port 8000 is in use, edit `inject_response.py` to use a different port
- **Large Requests**: Requests can be 500KB+ due to full conversation history
- **Binary Responses**: All responses are AWS Event Stream binary format

---

## Troubleshooting

**"Request not found"**
- Check that `DEBUG_MODE = True` in `kiropipe.py`
- Verify the request number exists in `posted/` directory

**"Connection refused" (injection tests)**
- Make sure `inject_response.py` is running
- Check the port is correct (default: 8000)

**"Module not found"**
- Install requirements: `pip install -r requirements.txt`
- Make sure you're running from the project root

**"Invalid binary format"**
- The encoder may have a bug
- Run `test_encoder.py` to verify encoding works
- Compare with captured real responses

---

## Contributing

When adding new tools:
1. Add them to this directory
2. Update this README
3. Follow the naming convention: `verb_noun.py`
4. Include usage examples in docstrings
5. Add error handling and helpful messages
