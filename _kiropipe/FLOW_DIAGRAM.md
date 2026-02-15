# KiroPipe Complete Flow Diagram

## Simple Message Flow (No Tools)

```
User types: "Hello"
     ↓
[Kiro] → Request #1
     ↓
{
  "conversationState": {
    "currentMessage": {
      "userInputMessage": {
        "content": "Hello",
        "tools": [...]  // Available tools
      }
    }
  }
}
     ↓
[Proxy] → Forward to Bridge (if enabled)
     ↓
[Bridge] → Translate to Anthropic
     ↓
{
  "model": "claude-3-5-sonnet-20241022",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "tools": [...]
}
     ↓
[Anthropic API] → Streaming response
     ↓
{
  "type": "content_block_delta",
  "delta": {"type": "text_delta", "text": "Hi there!"}
}
     ↓
[Bridge] → Translate to AWS Event Stream
     ↓
Binary: assistantResponseEvent {"content": "Hi there!"}
     ↓
[Proxy] → Return to Kiro
     ↓
[Kiro] → Display: "Hi there!"
```

## Tool Use Flow (Multi-Turn)

### Turn 1: User Message → LLM Requests Tools

```
User types: "Read file test.py"
     ↓
[Kiro] → Request #1
     ↓
{
  "conversationState": {
    "currentMessage": {
      "userInputMessage": {
        "content": "Read file test.py",
        "tools": [
          {"toolSpecification": {"name": "readFile", ...}}
        ]
      }
    }
  }
}
     ↓
[Bridge] → Translate to Anthropic
     ↓
{
  "messages": [
    {"role": "user", "content": "Read file test.py"}
  ],
  "tools": [
    {"name": "readFile", "input_schema": {...}}
  ]
}
     ↓
[Anthropic API] → Decides to use tool
     ↓
{
  "type": "content_block_start",
  "content_block": {
    "type": "tool_use",
    "id": "tool_123",
    "name": "readFile"
  }
}
{
  "type": "content_block_delta",
  "delta": {
    "type": "input_json_delta",
    "partial_json": "{\"path\""
  }
}
{
  "type": "content_block_delta",
  "delta": {
    "type": "input_json_delta",
    "partial_json": ": \"test.py\"}"
  }
}
     ↓
[Bridge] → Translate to AWS Event Stream
     ↓
Binary: toolUseEvent {"name": "readFile", "toolUseId": "tool_123", "input": "{\"path\""}
Binary: toolUseEvent {"name": "readFile", "toolUseId": "tool_123", "input": ": \"test.py\"}"}
Binary: toolUseEvent {"name": "readFile", "toolUseId": "tool_123", "input": ""}
     ↓
[Kiro] → Receives tool call
     ↓
[Kiro] → Executes readFile locally
     ↓
[Kiro] → Gets result: "def main():\n    print('hello')"
```

### Turn 2: Tool Results → LLM Final Response

```
[Kiro] → Request #2
     ↓
{
  "conversationState": {
    "currentMessage": {
      "userInputMessage": {
        "content": "",  // Empty!
        "toolResults": [
          {
            "toolUseId": "tool_123",
            "status": "success",
            "content": [
              {"text": "def main():\n    print('hello')"}
            ]
          }
        ],
        "tools": [...]  // Still available
      }
    }
  }
}
     ↓
[Bridge] → Translate to Anthropic
     ↓
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "tool_123",
          "content": "def main():\n    print('hello')"
        }
      ]
    }
  ],
  "tools": [...]
}
     ↓
[Anthropic API] → Sees tool result, responds
     ↓
{
  "type": "content_block_delta",
  "delta": {"type": "text_delta", "text": "The file contains..."}
}
     ↓
[Bridge] → Translate to AWS Event Stream
     ↓
Binary: assistantResponseEvent {"content": "The file contains..."}
     ↓
[Kiro] → Display: "The file contains..."
```

## Key Points

### 1. Conversation History is Included
- **CRITICAL**: Every request includes full conversation history
- Located in `conversationState.history` array
- Can be 200+ items (system prompt + all turns)
- This is why requests are 500KB+
- History format:
  ```json
  "history": [
    {"userInputMessage": {"content": "system prompt..."}},
    {"userInputMessage": {"content": "user message 1"}},
    {"assistantResponseMessage": {"content": "assistant response 1"}},
    {"userInputMessage": {"content": "user message 2"}},
    ...
  ]
  ```

### 2. Tool Calls Come FROM LLM
- LLM decides to use tools
- Returns tool calls in response (binary format)
- Kiro executes tools locally
- NOT sent in request from Kiro

### 2. Tool Results Go TO LLM
- Kiro executes tools
- Sends results in next request
- Request has empty content but toolResults array
- LLM sees results and responds with final answer

### 3. Binary Format
- ALL responses are AWS Event Stream binary
- Text responses: assistantResponseEvent
- Tool calls: toolUseEvent (streamed as chunks)
- Usage: meteringEvent
- Context: contextUsageEvent

### 4. Request Format
- Tools are wrapped in toolSpecification
- Tool results have content as array of {text: "..."}
- Empty content when sending tool results

## Bridge Translation

### Request Translation (AWS Q → Anthropic)

```python
# Extract user message
content = request['conversationState']['currentMessage']['userInputMessage']['content']

# Extract tools (unwrap toolSpecification)
tools = []
for tool in request['...']['tools']:
    tool_spec = tool['toolSpecification']
    tools.append({
        'name': tool_spec['name'],
        'description': tool_spec['description'],
        'input_schema': tool_spec['inputSchema']
    })

# Extract tool results (extract text from content array)
tool_results = []
for result in request['...']['toolResults']:
    text = result['content'][0]['text']  # Extract from array
    tool_results.append({
        'type': 'tool_result',
        'tool_use_id': result['toolUseId'],
        'content': text
    })
```

### Response Translation (Anthropic → AWS Q)

```python
# Text delta → assistantResponseEvent
if event['type'] == 'content_block_delta' and event['delta']['type'] == 'text_delta':
    yield encode_text_chunk(event['delta']['text'])

# Tool use → toolUseEvent (streamed)
if event['type'] == 'content_block_start' and event['content_block']['type'] == 'tool_use':
    tool_id = event['content_block']['id']
    tool_name = event['content_block']['name']

if event['type'] == 'content_block_delta' and event['delta']['type'] == 'input_json_delta':
    yield encode_tool_use_chunk(tool_name, tool_id, event['delta']['partial_json'])
```

## Complete Example

### User: "Create a file hello.py with print('hello')"

**Request #1**: User message
```json
{"content": "Create a file hello.py with print('hello')"}
```

**Response #1**: Tool call (binary)
```
toolUseEvent: {"name": "fsWrite", "toolUseId": "tool_abc", "input": "{\"path\""}
toolUseEvent: {"name": "fsWrite", "toolUseId": "tool_abc", "input": ": \"hello.py\", \"text\""}
toolUseEvent: {"name": "fsWrite", "toolUseId": "tool_abc", "input": ": \"print('hello')\"}"}
```

**Kiro executes**: fsWrite("hello.py", "print('hello')")

**Request #2**: Tool result
```json
{
  "content": "",
  "toolResults": [{
    "toolUseId": "tool_abc",
    "status": "success",
    "content": [{"text": "Created the hello.py file."}]
  }]
}
```

**Response #2**: Final answer (binary)
```
assistantResponseEvent: {"content": "I've created"}
assistantResponseEvent: {"content": " the file"}
assistantResponseEvent: {"content": " hello.py"}
assistantResponseEvent: {"content": " with the print statement."}
meteringEvent: {"usage": 0.15, "unit": "credit"}
```

**Kiro displays**: "I've created the file hello.py with the print statement."

## Summary

The bridge works by:
1. Translating AWS Q requests to Anthropic format
2. Calling Anthropic API
3. Translating streaming responses back to AWS Event Stream binary
4. Kiro handles tool execution locally
5. Tool results come back in next request
6. Process repeats until final answer

All responses are binary AWS Event Stream format, regardless of content type (text or tool calls).
