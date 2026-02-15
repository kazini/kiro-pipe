# KiroPipe Module Structure

## Overview
KiroPipe intercepts Kiro's AWS Q API traffic and enables custom LLM backend usage.

## Directory Structure

```
_kiropipe/
├── engine/              # Core functionality (required for bridge)
│   ├── decode_event_stream.py      # Decodes AWS Event Stream binary format
│   ├── event_stream_encoder.py     # Encodes responses to AWS Event Stream
│   └── reconstruct_messages.py     # Reconstructs full messages from events
│
├── tools/               # Development and testing utilities
│   ├── test_encoder.py             # Tests encoder/decoder functionality
│   ├── analyze_interaction_pattern.py  # Analyzes request/response patterns
│   └── [frida scripts and other dev tools]
│
├── debug_logs/          # Debug output (created when DEBUG_MODE=True)
│   └── interactions/
│       ├── posted/      # Captured requests
│       └── responses/   # Captured responses
│
├── BRIDGE_DESIGN.md     # API bridge architecture documentation
├── bridge_requirements.txt  # Python dependencies for bridge
└── KIROPIPE_DEV_JOURNAL.md  # Development history

```

## Core Engine Scripts

### decode_event_stream.py
Decodes AWS Event Stream binary responses to JSON format.

**Usage**:
```bash
python _kiropipe/engine/decode_event_stream.py
```

**Purpose**: Analyzes captured binary responses and extracts events (text chunks, tool uses, metering, context usage).

### event_stream_encoder.py
Encodes responses into AWS Event Stream binary format.

**Usage**:
```bash
python _kiropipe/engine/event_stream_encoder.py
```

**Purpose**: Core component for the API bridge - converts LLM responses back to Kiro-compatible format.

**Functions**:
- `encode_event()` - Main event encoder
- `encode_text_chunk()` - Encode text content
- `encode_tool_use_chunk()` - Encode tool calls
- `encode_metering()` - Encode usage metrics
- `encode_context_usage()` - Encode context percentage
- `encode_streaming_response()` - Build complete streaming response

### reconstruct_messages.py
Reconstructs full AI messages from decoded event streams.

**Usage**:
```bash
python _kiropipe/engine/reconstruct_messages.py
```

**Purpose**: Concatenates text chunks and displays complete messages with metadata.

## Development Tools

### test_encoder.py
Tests the encoder/decoder round-trip and validates format against captured responses.

**Usage**:
```bash
python _kiropipe/tools/test_encoder.py
```

**Tests**:
1. Round-trip encoding/decoding
2. Binary structure analysis
3. Comparison with captured AWS Q responses

### analyze_interaction_pattern.py
Analyzes request/response patterns to detect multi-step processing.

**Usage**:
```bash
python _kiropipe/tools/analyze_interaction_pattern.py
```

**Purpose**: Determines if AWS Q does additional processing or direct LLM calls.

## Running KiroPipe

Main launcher (in project root):
```bash
python kiropipe.py [port]
```

**Configuration** (edit top of kiropipe.py):
- `DEFAULT_PORT` - Proxy port (default: 29974)
- `KIRO_EXE_PATH` - Custom Kiro.exe path (or None for auto-detect)
- `BLOCK_TELEMETRY` - Block telemetry (default: True)
- `BLOCK_UPDATES` - Block update checks (default: True)
- `BLOCK_USAGE_LIMITS` - Block usage limits (default: True)
- `DEBUG_MODE` - Enable detailed logging (default: True)

## Next Steps

See `BRIDGE_DESIGN.md` for the API bridge implementation plan.
