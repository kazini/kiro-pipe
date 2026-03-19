# KiroPipe Implementation Plan

## Overview
This document outlines the implementation plan for completing KiroPipe's core functionality, focusing on retry logic, usage tracking, and format translation validation.

## Current Status Analysis

### ✅ Completed Features
- AWS Event Stream encoder/decoder
- Basic request translation (AWS Q → Anthropic/OpenAI)
- Basic response translation (Anthropic/OpenAI → AWS Event Stream)
- Configuration management
- Model injection
- Debug logging and traffic capture
- Proxy interception

### ❌ Missing/Incomplete Features
1. **Exponential Backoff & Retries**
   - No retry logic for failed API calls
   - No exponential backoff implementation
   - No rate limit handling

2. **Usage Tracking**
   - Basic token counting exists but incomplete
   - No persistent usage tracking across sessions
   - No per-model usage statistics
   - Metering events generated but not validated

3. **Format Translation Validation**
   - Translation logic exists but needs comprehensive testing
   - Tool use translation may have edge cases
   - Conversation history reconstruction needs validation
   - Binary format encoding needs verification

4. **Error Handling**
   - Basic error handling exists
   - No graceful degradation for API failures
   - Limited error reporting to user

## Implementation Tasks

### Phase 1: Retry Logic & Error Handling (Priority: HIGH)

#### Task 1.1: Implement Exponential Backoff
**File:** `_kiropipe/engine/retry_handler.py` (NEW)

**Requirements:**
- Exponential backoff with jitter
- Configurable max retries (default: 3)
- Configurable base delay (default: 1s)
- Configurable max delay (default: 60s)
- Retry on specific HTTP status codes: 429, 500, 502, 503, 504
- Don't retry on: 400, 401, 403, 404

**Implementation:**
```python
import time
import random
from typing import Callable, Any, Optional
import httpx

class RetryHandler:
    def __init__(self, max_retries=3, base_delay=1.0, max_delay=60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter"""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        return delay + jitter
    
    def should_retry(self, status_code: int, attempt: int) -> bool:
        """Determine if request should be retried"""
        if attempt >= self.max_retries:
            return False
        return status_code in [429, 500, 502, 503, 504]
    
    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        # Implementation details
```

#### Task 1.2: Integrate Retry Logic into API Calls
**Files to modify:**
- `kiropipe.py` (Anthropic/LiteLLM API calls)
- `_kiropipe/engine/bridge_server.py` (if exists)

**Changes:**
- Wrap all API calls with retry handler
- Add timeout configuration
- Implement circuit breaker pattern for repeated failures

#### Task 1.3: Enhanced Error Handling
**Requirements:**
- Catch and log all API errors
- Return user-friendly error messages to Kiro
- Encode errors as AWS Event Stream format
- Add error event type: `errorEvent`

### Phase 2: Usage Tracking & Metering (Priority: HIGH)

#### Task 2.1: Comprehensive Token Tracking
**File:** `_kiropipe/engine/usage_tracker.py` (NEW)

**Requirements:**
- Track input/output tokens per request
- Track tokens per model
- Track tokens per conversation
- Track tokens per session
- Persist usage data to JSON file
- Calculate costs based on model pricing

**Data Structure:**
```python
{
  "sessions": {
    "session_id": {
      "start_time": "2024-01-01T00:00:00Z",
      "end_time": "2024-01-01T01:00:00Z",
      "conversations": {
        "conversation_id": {
          "model": "claude-3-5-sonnet-20241022",
          "requests": [
            {
              "timestamp": "2024-01-01T00:00:00Z",
              "input_tokens": 100,
              "output_tokens": 50,
              "total_tokens": 150,
              "cost": 0.0015
            }
          ],
          "total_input_tokens": 100,
          "total_output_tokens": 50,
          "total_cost": 0.0015
        }
      }
    }
  }
}
```

#### Task 2.2: Extract Usage from API Responses
**Files to modify:**
- `_kiropipe/engine/response_translator.py`

**Changes:**
- Extract token counts from Anthropic responses (`usage` field)
- Extract token counts from OpenAI responses (`usage` field)
- Pass usage data to usage tracker
- Validate metering events match actual usage

#### Task 2.3: Usage Reporting
**File:** `_kiropipe/engine/usage_reporter.py` (NEW)

**Requirements:**
- Generate usage reports per session
- Generate usage reports per model
- Generate usage reports per time period
- Export to CSV/JSON
- Display in console on shutdown

### Phase 3: Format Translation Validation (Priority: MEDIUM)

#### Task 3.1: Request Translation Tests
**File:** `_kiropipe/devtools/test_request_translation.py` (NEW)

**Test Cases:**
1. Simple user message (no history, no tools)
2. User message with conversation history
3. User message with tool definitions
4. User message with tool results
5. User message with multiple tool results
6. User message with images (if supported)
7. Edge cases: empty messages, very long messages, special characters

#### Task 3.2: Response Translation Tests
**File:** `_kiropipe/devtools/test_response_translation.py` (NEW)

**Test Cases:**
1. Simple text response
2. Streaming text response (word by word)
3. Tool use response (single tool)
4. Tool use response (multiple tools)
5. Mixed response (text + tool use)
6. Response with usage metrics
7. Error responses
8. Edge cases: empty responses, very long responses

#### Task 3.3: Binary Format Validation
**File:** `_kiropipe/devtools/test_event_stream_format.py` (NEW)

**Test Cases:**
1. Encode → Decode round-trip
2. Compare with real AWS Q responses
3. Validate CRC checksums
4. Validate header format
5. Validate payload format
6. Test with Kiro (end-to-end)

#### Task 3.4: Tool Use Translation Validation
**File:** `_kiropipe/devtools/test_tool_translation.py` (NEW)

**Test Cases:**
1. Tool definition translation (AWS Q → Anthropic)
2. Tool definition translation (AWS Q → OpenAI)
3. Tool use translation (Anthropic → AWS Q)
4. Tool use translation (OpenAI → AWS Q)
5. Tool result translation (AWS Q → Anthropic)
6. Tool result translation (AWS Q → OpenAI)
7. Multiple tools in single request
8. Nested tool calls

### Phase 4: Integration & Testing (Priority: MEDIUM)

#### Task 4.1: End-to-End Testing
**File:** `_kiropipe/devtools/test_e2e.py` (NEW)

**Test Scenarios:**
1. Simple conversation (3-5 turns)
2. Conversation with tool use
3. Conversation with multiple models
4. Conversation with errors and retries
5. Long conversation (20+ turns)
6. Concurrent conversations

#### Task 4.2: Performance Testing
**File:** `_kiropipe/devtools/test_performance.py` (NEW)

**Metrics:**
- Latency (request → first token)
- Throughput (tokens per second)
- Memory usage
- CPU usage
- Network bandwidth

#### Task 4.3: Stress Testing
**Requirements:**
- Test with high request rate
- Test with large payloads
- Test with many concurrent conversations
- Test with API failures
- Test with network issues

### Phase 5: Documentation & Polish (Priority: LOW)

#### Task 5.1: Update Documentation
**Files to update:**
- `README.md` - Add retry/usage tracking features
- `_kiropipe/devtools/README.md` - Add new test tools
- `_kiropipe/KIROPIPE_DEV_JOURNAL.md` - Document implementation

#### Task 5.2: Configuration Examples
**Files to create:**
- `_kiropipe/kiropipe_config.yaml.example` - Add retry/usage config
- `_kiropipe/docs/CONFIGURATION.md` - Detailed config guide

#### Task 5.3: Error Messages
**Requirements:**
- User-friendly error messages
- Troubleshooting guide
- Common issues and solutions

## Implementation Order

### Week 1: Retry Logic
- Day 1-2: Implement `retry_handler.py`
- Day 3-4: Integrate into `kiropipe.py`
- Day 5: Test and debug

### Week 2: Usage Tracking
- Day 1-2: Implement `usage_tracker.py`
- Day 3: Integrate into response translator
- Day 4: Implement `usage_reporter.py`
- Day 5: Test and validate

### Week 3: Format Validation
- Day 1: Request translation tests
- Day 2: Response translation tests
- Day 3: Binary format tests
- Day 4: Tool translation tests
- Day 5: Fix issues found

### Week 4: Integration & Polish
- Day 1-2: End-to-end testing
- Day 3: Performance testing
- Day 4: Documentation
- Day 5: Final review and release

## Success Criteria

### Retry Logic
- ✅ All API calls have retry logic
- ✅ Exponential backoff works correctly
- ✅ Rate limits are handled gracefully
- ✅ Errors are reported to user

### Usage Tracking
- ✅ Token counts match API responses
- ✅ Usage data persists across sessions
- ✅ Reports are accurate and useful
- ✅ Costs are calculated correctly

### Format Translation
- ✅ All test cases pass
- ✅ Round-trip encoding works
- ✅ Kiro displays responses correctly
- ✅ Tool use works end-to-end

### Integration
- ✅ End-to-end tests pass
- ✅ Performance is acceptable (<100ms overhead)
- ✅ No memory leaks
- ✅ Stable under load

## Notes

### Known Issues
1. Tool use translation may not handle all edge cases
2. Conversation history reconstruction needs validation
3. Binary format CRC validation needs testing
4. Usage tracking for LiteLLM providers needs special handling

### Future Enhancements
1. Caching layer for repeated requests
2. Request/response compression
3. Multi-provider fallback
4. A/B testing between models
5. Cost optimization suggestions
6. Usage alerts and limits

## References

### AWS Event Stream Format
- Binary format with CRC checksums
- Headers: `:event-type`, `:content-type`, `:message-type`
- Event types: `assistantResponseEvent`, `toolUseEvent`, `meteringEvent`, `contextUsageEvent`

### Anthropic API
- Messages API with streaming
- Tool use format
- Usage tracking in response

### OpenAI API
- Chat Completions API with streaming
- Function calling format
- Usage tracking in response

### Sample Files
- `samples/post/request_*.json` - AWS Q request examples
- `samples/responses/response_*.bin` - AWS Q response examples
- `samples/py_kiropipe_output_example.txt` - Console output with network traffic
