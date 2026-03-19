#!/usr/bin/env python3
"""
Integration Test
Tests the complete flow: retry handler, usage tracker, and format translation
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.retry_handler import RetryHandler, RetryConfig
from engine.usage_tracker import UsageTracker
from engine.request_translator import translate_to_anthropic, translate_to_openai
from engine.response_translator import translate_anthropic_stream, translate_openai_stream
from engine.decode_event_stream import decode_event_stream


def test_retry_handler():
    """Test retry handler with mock API calls"""
    print("\n" + "="*60)
    print("Test 1: Retry Handler")
    print("="*60)
    
    retry_handler = RetryHandler(RetryConfig(
        max_retries=3,
        base_delay=0.1,  # Fast for testing
        max_delay=1.0
    ))
    
    # Test 1: Successful call (no retry)
    call_count = 0
    
    def successful_call():
        nonlocal call_count
        call_count += 1
        return {"status": "success", "data": "test"}
    
    result = retry_handler.execute_with_retry(successful_call)
    assert result["status"] == "success"
    assert call_count == 1
    print("✓ Successful call (no retry): PASSED")
    
    # Test 2: Retry on exception
    call_count = 0
    
    def failing_then_success():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Network error")
        return {"status": "success"}
    
    result = retry_handler.execute_with_retry(failing_then_success)
    assert result["status"] == "success"
    assert call_count == 3
    print("✓ Retry on exception: PASSED")
    
    print("\n✓ All retry handler tests passed!")


def test_usage_tracker():
    """Test usage tracker"""
    print("\n" + "="*60)
    print("Test 2: Usage Tracker")
    print("="*60)
    
    import tempfile
    temp_file = Path(tempfile.mktemp(suffix='.json'))
    
    tracker = UsageTracker(temp_file)
    
    # Track some requests
    tracker.track_request(
        conversation_id='conv_1',
        model='claude-3-5-sonnet-20241022',
        input_tokens=100,
        output_tokens=50
    )
    
    tracker.track_request(
        conversation_id='conv_1',
        model='claude-3-5-sonnet-20241022',
        input_tokens=200,
        output_tokens=100
    )
    
    tracker.track_request(
        conversation_id='conv_2',
        model='gpt-4-turbo',
        input_tokens=150,
        output_tokens=75
    )
    
    # Verify conversation stats
    conv_stats = tracker.get_conversation_stats('conv_1')
    assert conv_stats is not None
    assert conv_stats['total_input_tokens'] == 300
    assert conv_stats['total_output_tokens'] == 150
    print("✓ Conversation tracking: PASSED")
    
    # Verify session stats
    session_stats = tracker.get_session_stats()
    assert session_stats is not None
    assert session_stats['total_requests'] == 3
    assert session_stats['total_input_tokens'] == 450
    assert session_stats['total_output_tokens'] == 225
    print("✓ Session tracking: PASSED")
    
    # Verify model stats
    model_stats = tracker.get_model_stats()
    assert 'claude-3-5-sonnet-20241022' in model_stats
    assert 'gpt-4-turbo' in model_stats
    assert model_stats['claude-3-5-sonnet-20241022']['requests'] == 2
    assert model_stats['gpt-4-turbo']['requests'] == 1
    print("✓ Model tracking: PASSED")
    
    # Cleanup
    temp_file.unlink(missing_ok=True)
    
    print("\n✓ All usage tracker tests passed!")


def test_request_translation():
    """Test request translation with tools and history"""
    print("\n" + "="*60)
    print("Test 3: Request Translation")
    print("="*60)
    
    # Test with tools
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Read the file test.py',
                    'userInputMessageContext': {
                        'tools': [
                            {
                                'toolSpecification': {
                                    'name': 'readFile',
                                    'description': 'Read a file',
                                    'inputSchema': {
                                        'type': 'object',
                                        'properties': {
                                            'path': {'type': 'string'}
                                        },
                                        'required': ['path']
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
    
    # Translate to Anthropic
    anthropic_req = translate_to_anthropic(aws_request)
    assert 'messages' in anthropic_req
    assert len(anthropic_req['messages']) == 1
    assert anthropic_req['messages'][0]['role'] == 'user'
    assert 'tools' in anthropic_req
    assert len(anthropic_req['tools']) == 1
    assert anthropic_req['tools'][0]['name'] == 'readFile'
    print("✓ Anthropic translation with tools: PASSED")
    
    # Translate to OpenAI
    openai_req = translate_to_openai(aws_request)
    assert 'messages' in openai_req
    assert len(openai_req['messages']) == 1
    assert openai_req['messages'][0]['role'] == 'user'
    assert 'tools' in openai_req
    assert len(openai_req['tools']) == 1
    assert openai_req['tools'][0]['type'] == 'function'
    assert openai_req['tools'][0]['function']['name'] == 'readFile'
    print("✓ OpenAI translation with tools: PASSED")
    
    print("\n✓ All request translation tests passed!")


def test_response_translation():
    """Test response translation"""
    print("\n" + "="*60)
    print("Test 4: Response Translation")
    print("="*60)
    
    # Test Anthropic text response
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 100}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'Hello'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': ' world'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 50}},
        {'type': 'message_stop'}
    ]
    
    # Track usage
    tracked_input = 0
    tracked_output = 0
    
    def usage_callback(input_tokens, output_tokens):
        nonlocal tracked_input, tracked_output
        tracked_input = input_tokens
        tracked_output = output_tokens
    
    aws_binary = b''.join(translate_anthropic_stream(
        iter(anthropic_events),
        include_usage=True,
        usage_callback=usage_callback
    ))
    
    assert len(aws_binary) > 0
    assert tracked_input == 100
    assert tracked_output == 50
    print("✓ Anthropic text response with usage tracking: PASSED")
    
    # Decode and verify
    events = decode_event_stream(aws_binary)
    assert len(events) > 0
    
    # Check for text events
    text_events = [e for e in events if e['headers'].get(':event-type') == 'assistantResponseEvent']
    assert len(text_events) > 0
    print("✓ AWS event stream decoding: PASSED")
    
    # Test Anthropic tool use response
    anthropic_tool_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 150}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'id': 'tool_123', 'name': 'readFile'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ': "test.py"}'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 30}},
        {'type': 'message_stop'}
    ]
    
    tracked_input = 0
    tracked_output = 0
    
    aws_tool_binary = b''.join(translate_anthropic_stream(
        iter(anthropic_tool_events),
        include_usage=True,
        usage_callback=usage_callback
    ))
    
    assert len(aws_tool_binary) > 0
    assert tracked_input == 150
    assert tracked_output == 30
    print("✓ Anthropic tool use response with usage tracking: PASSED")
    
    # Decode and verify tool events
    tool_events = decode_event_stream(aws_tool_binary)
    tool_use_events = [e for e in tool_events if e['headers'].get(':event-type') == 'toolUseEvent']
    assert len(tool_use_events) > 0
    
    # Check for stop flag in final tool event
    final_tool_event = tool_use_events[-1]
    assert final_tool_event['payload'].get('stop') == True
    print("✓ Tool use stop flag: PASSED")
    
    print("\n✓ All response translation tests passed!")


def test_end_to_end():
    """Test complete flow: request → translation → response → translation"""
    print("\n" + "="*60)
    print("Test 5: End-to-End Integration")
    print("="*60)
    
    # Create AWS request with tools
    aws_request = {
        'conversationState': {
            'conversationId': 'e2e-test',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'List files in current directory',
                    'userInputMessageContext': {
                        'tools': [
                            {
                                'toolSpecification': {
                                    'name': 'listDirectory',
                                    'description': 'List directory contents',
                                    'inputSchema': {
                                        'type': 'object',
                                        'properties': {
                                            'path': {'type': 'string'}
                                        },
                                        'required': ['path']
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
    
    # Translate request
    anthropic_req = translate_to_anthropic(aws_request, model='claude-3-5-sonnet-20241022')
    assert 'messages' in anthropic_req
    assert 'tools' in anthropic_req
    print("✓ Request translation: PASSED")
    
    # Simulate Anthropic response (tool use)
    anthropic_response = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 200}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'id': 'tool_456', 'name': 'listDirectory'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path": "."}'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 40}},
        {'type': 'message_stop'}
    ]
    
    # Track usage
    import tempfile
    temp_file = Path(tempfile.mktemp(suffix='.json'))
    tracker = UsageTracker(temp_file)
    
    def usage_callback(input_tokens, output_tokens):
        tracker.track_request(
            conversation_id='e2e-test',
            model='claude-3-5-sonnet-20241022',
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    
    # Translate response
    aws_binary = b''.join(translate_anthropic_stream(
        iter(anthropic_response),
        include_usage=True,
        usage_callback=usage_callback
    ))
    
    assert len(aws_binary) > 0
    print("✓ Response translation: PASSED")
    
    # Verify usage tracking
    conv_stats = tracker.get_conversation_stats('e2e-test')
    assert conv_stats is not None
    assert conv_stats['total_input_tokens'] == 200
    assert conv_stats['total_output_tokens'] == 40
    print("✓ Usage tracking: PASSED")
    
    # Decode AWS binary
    events = decode_event_stream(aws_binary)
    assert len(events) > 0
    
    # Verify tool use events
    tool_events = [e for e in events if e['headers'].get(':event-type') == 'toolUseEvent']
    assert len(tool_events) > 0
    assert tool_events[-1]['payload'].get('stop') == True
    print("✓ Tool use events: PASSED")
    
    # Verify metering events
    metering_events = [e for e in events if e['headers'].get(':event-type') == 'meteringEvent']
    assert len(metering_events) > 0
    print("✓ Metering events: PASSED")
    
    # Cleanup
    temp_file.unlink(missing_ok=True)
    
    print("\n✓ End-to-end integration test passed!")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("KiroPipe Integration Tests")
    print("="*60)
    
    try:
        test_retry_handler()
        test_usage_tracker()
        test_request_translation()
        test_response_translation()
        test_end_to_end()
        
        print("\n" + "="*60)
        print("✓ ALL INTEGRATION TESTS PASSED!")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
