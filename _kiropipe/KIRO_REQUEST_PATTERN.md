# Kiro's Request Pattern Analysis

## Overview

Kiro uses a **two-phase request pattern** for handling user messages. This is an optimization to reduce costs and improve response time.

## The Two-Phase Pattern

### Phase 1: Intent Classification

**Purpose**: Quickly classify the user's intent to determine the execution mode

**Characteristics**:
- **Header**: `x-amzn-kiro-agent-mode: intent-classification`
- **Model**: `simple-task` (lightweight, fast model)
- **Request Size**: Small (~4-5KB)
- **History**: Contains intent classification prompt
- **Response**: JSON object with confidence scores

**Example Request**:
```json
{
  "conversationState": {
    "agentTaskType": "vibe",
    "currentMessage": {
      "userInputMessage": {
        "content": "User's actual message",
        "modelId": "simple-task"
      }
    },
    "history": [
      {
        "userInputMessage": {
          "content": "Intent classification prompt...",
          "modelId": "simple-task"
        }
      }
    ]
  }
}
```

**Example Response**:
```json
{
  "chat": 0.0,
  "do": 0.9,
  "spec": 0.1
}
```

**Intent Categories**:
- **chat**: Conversational, informational queries
- **do**: Action requests (file operations, code changes)
- **spec**: Specification/planning mode

### Phase 2: Task Execution

**Purpose**: Execute the actual task based on classified intent

**Characteristics**:
- **Header**: `x-amzn-kiro-agent-mode: vibe` (or other mode based on classification)
- **Model**: `claude-haiku-4.5` or other full-capability model
- **Request Size**: Large (80-100KB+) - includes full context
- **History**: Complete conversation history
- **Tools**: Full tool definitions (20+ tools)
- **Response**: Actual task execution with tool calls

**Example Request**:
```json
{
  "conversationState": {
    "agentTaskType": "vibe",
    "currentMessage": {
      "userInputMessage": {
        "content": "User's actual message",
        "modelId": "claude-haiku-4.5",
        "userInputMessageContext": {
          "tools": [...], // 20+ tool definitions
          "toolResults": [...] // Previous tool results
        }
      }
    },
    "history": [...] // Full conversation history
  }
}
```

## Request Flow Example

For a single user message: "Please read the file test.txt"

```
User Message
    ↓
┌─────────────────────────────────────────┐
│ Phase 1: Intent Classification          │
├─────────────────────────────────────────┤
│ Model: simple-task                      │
│ Size: 4KB                               │
│ Time: ~200ms                            │
│ Cost: ~$0.0001                          │
│ Result: {"do": 0.95, "chat": 0.05}     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Phase 2: Task Execution                 │
├─────────────────────────────────────────┤
│ Model: claude-haiku-4.5                 │
│ Size: 90KB                              │
│ Time: ~2000ms                           │
│ Cost: ~$0.01                            │
│ Result: Tool calls + response           │
└─────────────────────────────────────────┘
    ↓
Response to User
```

## Why This Pattern?

### Benefits

1. **Cost Optimization**
   - Intent classification uses a cheap model
   - Only use expensive models for actual work
   - Saves ~90% on classification costs

2. **Speed Optimization**
   - Fast classification (200ms vs 2000ms)
   - User sees faster initial response
   - Better perceived performance

3. **Routing Flexibility**
   - Different modes can use different models
   - Can route to specialized models
   - Better resource allocation

4. **Context Management**
   - Classification doesn't need full context
   - Reduces token usage
   - Faster processing

### Trade-offs

1. **Extra Request**
   - Two API calls instead of one
   - Slightly more network overhead
   - More complex to track

2. **Latency**
   - Total time = classification + execution
   - But classification is fast, so minimal impact

3. **Complexity**
   - More complex request flow
   - Need to handle both request types
   - More state to track

## Implications for KiroPipe

### 1. Request Handling

**DO**:
- ✅ Allow both intent classification and task execution requests
- ✅ Preserve the `x-amzn-kiro-agent-mode` header
- ✅ Handle both `simple-task` and full models

**DON'T**:
- ❌ Block intent classification requests
- ❌ Merge the two requests into one
- ❌ Interfere with the workflow

### 2. Usage Tracking

Track both phases separately:

```python
# Phase 1: Intent Classification
usage_tracker.track_request(
    conversation_id='conv_123',
    model='simple-task',
    input_tokens=100,
    output_tokens=10,
    metadata={'phase': 'intent_classification'}
)

# Phase 2: Task Execution
usage_tracker.track_request(
    conversation_id='conv_123',
    model='claude-haiku-4.5',
    input_tokens=5000,
    output_tokens=500,
    metadata={'phase': 'task_execution'}
)
```

### 3. Custom Model Routing

When routing to custom models:

```python
# Check if it's intent classification
if 'x-amzn-kiro-agent-mode' in headers:
    mode = headers['x-amzn-kiro-agent-mode']
    
    if mode == 'intent-classification':
        # Use a fast, cheap model for classification
        # Or let Kiro handle it (don't intercept)
        pass
    
    elif mode == 'vibe':
        # Route to custom model for task execution
        route_to_custom_model(request)
```

### 4. Retry Logic

Apply retry logic to both phases:

```python
# Intent classification - fast retries
retry_config_classification = RetryConfig(
    max_retries=2,
    base_delay=0.5,
    max_delay=5.0
)

# Task execution - normal retries
retry_config_execution = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0
)
```

## Detection Logic

To detect which phase a request is in:

```python
def get_request_phase(request):
    """Determine which phase this request is in"""
    
    # Check header
    headers = request.get('headers', {})
    mode = headers.get('x-amzn-kiro-agent-mode', '')
    
    if mode == 'intent-classification':
        return 'intent_classification'
    
    # Check model
    body = json.loads(request.get('body', '{}'))
    model_id = (
        body.get('conversationState', {})
        .get('currentMessage', {})
        .get('userInputMessage', {})
        .get('modelId', '')
    )
    
    if model_id == 'simple-task':
        return 'intent_classification'
    
    # Check history for intent classification prompt
    history = body.get('conversationState', {}).get('history', [])
    if history:
        first_msg = history[0].get('userInputMessage', {}).get('content', '')
        if 'intent classifier' in first_msg.lower():
            return 'intent_classification'
    
    return 'task_execution'
```

## Conversation Flow

A typical conversation with tool use:

```
1. User: "Read file test.txt"
   ├─ Request #1: Intent Classification (simple-task)
   │  └─ Response: {"do": 0.95}
   └─ Request #2: Task Execution (claude-haiku-4.5)
      └─ Response: Tool call readFile

2. Kiro executes tool
   └─ Request #3: Task Execution with tool result (claude-haiku-4.5)
      └─ Response: "The file contains..."

3. User: "What's in it?"
   ├─ Request #4: Intent Classification (simple-task)
   │  └─ Response: {"chat": 0.9}
   └─ Request #5: Task Execution (claude-haiku-4.5)
      └─ Response: "Based on the file..."
```

## Summary

- **Pattern**: Two-phase (classification → execution)
- **Purpose**: Cost and speed optimization
- **Detection**: Check `x-amzn-kiro-agent-mode` header or model ID
- **Handling**: Allow both phases, track separately
- **Routing**: Can intercept execution phase, preserve classification

This pattern is a smart optimization by Kiro and should be preserved in KiroPipe's implementation.
