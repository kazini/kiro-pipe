#!/usr/bin/env python3
"""
Test Anthropic Translation
Comprehensive tests for AWS Q ↔ Anthropic format translation
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.request_translator import translate_to_anthropic, extract_tools, extract_tool_results
from engine.response_translator import translate_anthropic_stream
from engine.decode_event_stream import decode_event_stream


def test_simple_message():
    """Test 1: Simple user message (no history, no tools)"""
    print("\n" + "="*60)
    print("Test 1: Simple User Message")
    print("="*60)
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Hello, how are you?',
                    'modelId': 'claude-3-5-sonnet-20241022',
                    'origin': 'AI_EDITOR'
                }
            }
        }
    }
    
    anthropic_request = translate_to_anthropic(aws_request)
    
    print("\nAWS Q Request:")
    print(json.dumps(aws_request, indent=2))
    
    print("\nAntropic Request:")
    print(json.dumps(anthropic_request, indent=2))
    
    # Validate
    assert anthropic_request['model'] == 'claude-3-5-sonnet-20241022'
    assert len(anthropic_request['messages']) == 1
    assert anthropic_request['messages'][0]['role'] == 'user'
    assert anthropic_request['messages'][0]['content'] == 'Hello, how are you?'
    assert anthropic_request['stream'] == True
    assert 'tools' not in anthropic_request
    
    print("\n✓ Test passed!")


def test_message_with_history():
    """Test 2: User message with conversation history"""
    print("\n" + "="*60)
    print("Test 2: Message with History")
    print("="*60)
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'What about Python?',
                    'modelId': 'claude-3-5-sonnet-20241022',
                    'origin': 'AI_EDITOR'
                }
            },
            'history': [
                {
                    'userInputMessage': {
                        'content': 'Tell me about JavaScript',
                        'modelId': 'claude-3-5-sonnet-20241022',
                        'origin': 'AI_EDITOR'
                    }
                },
                {
                    'assistantResponseMessage': {
                        'content': 'JavaScript is a programming language...',
                        'toolUses': []
                    }
                }
            ]
        }
    }
    
    anthropic_request = translate_to_anthropic(aws_request)
    
    print("\nAntropic Request:")
    print(json.dumps(anthropic_request, indent=2))
    
    # Validate
    assert len(anthropic_request['messages']) == 3
    assert anthropic_request['messages'][0]['role'] == 'user'
    assert anthropic_request['messages'][0]['content'] == 'Tell me about JavaScript'
    assert anthropic_request['messages'][1]['role'] == 'assistant'
    assert anthropic_request['messages'][2]['role'] == 'user'
    assert anthropic_request['messages'][2]['content'] == 'What about Python?'
    
    print("\n✓ Test passed!")


def test_message_with_tools():
    """Test 3: User message with tool definitions"""
    print("\n" + "="*60)
    print("Test 3: Message with Tools")
    print("="*60)
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Read the file test.py',
                    'modelId': 'claude-3-5-sonnet-20241022',
                    'origin': 'AI_EDITOR',
                    'userInputMessageContext': {
                        'tools': [
                            {
                                'toolSpecification': {
                                    'name': 'readFile',
                                    'description': 'Read a file from the filesystem',
                                    'inputSchema': {
                                        'json': {
                                            'type': 'object',
                                            'properties': {
                                                'path': {
                                                    'type': 'string',
                                                    'description': 'Path to the file'
                                                }
                                            },
                                            'required': ['path']
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
    
    anthropic_request = translate_to_anthropic(aws_request)
    
    print("\nAntropic Request:")
    print(json.dumps(anthropic_request, indent=2))
    
    # Validate
    assert 'tools' in anthropic_request
    assert len(anthropic_request['tools']) == 1
    assert anthropic_request['tools'][0]['name'] == 'readFile'
    assert 'input_schema' in anthropic_request['tools'][0]
    
    print("\n✓ Test passed!")


def test_message_with_tool_results():
    """Test 4: User message with tool results"""
    print("\n" + "="*60)
    print("Test 4: Message with Tool Results")
    print("="*60)
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': '',
                    'modelId': 'claude-3-5-sonnet-20241022',
                    'origin': 'AI_EDITOR',
                    'userInputMessageContext': {
                        'toolResults': [
                            {
                                'toolUseId': 'tool_123',
                                'status': 'success',
                                'content': [
                                    {
                                        'text': 'File contents: Hello, world!'
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }
    
    anthropic_request = translate_to_anthropic(aws_request)
    
    print("\nAntropic Request:")
    print(json.dumps(anthropic_request, indent=2))
    
    # Validate
    assert len(anthropic_request['messages']) == 1
    assert anthropic_request['messages'][0]['role'] == 'user'
    assert isinstance(anthropic_request['messages'][0]['content'], list)
    
    content = anthropic_request['messages'][0]['content']
    tool_result = next((c for c in content if c.get('type') == 'tool_result'), None)
    assert tool_result is not None
    assert tool_result['tool_use_id'] == 'tool_123'
    assert 'File contents: Hello, world!' in tool_result['content']
    
    print("\n✓ Test passed!")


def test_response_translation():
    """Test 5: Anthropic response → AWS Event Stream"""
    print("\n" + "="*60)
    print("Test 5: Response Translation")
    print("="*60)
    
    # Simulate Anthropic streaming response
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 100}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'Hello'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': ' world'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': '!'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 50}},
        {'type': 'message_stop'}
    ]
    
    # Track usage
    usage_data = {}
    
    def usage_callback(input_tokens, output_tokens):
        usage_data['input'] = input_tokens
        usage_data['output'] = output_tokens
    
    # Translate to AWS Event Stream
    aws_stream = b''.join(translate_anthropic_stream(
        iter(anthropic_events),
        usage_callback=usage_callback
    ))
    
    print(f"\nGenerated {len(aws_stream)} bytes of AWS Event Stream")
    print(f"First 100 bytes (hex): {aws_stream[:100].hex()}")
    
    # Decode and validate
    events = decode_event_stream(aws_stream)
    print(f"\nDecoded {len(events)} events:")
    
    text_content = []
    for i, event in enumerate(events, 1):
        event_type = event['headers'].get(':event-type')
        print(f"  {i}. {event_type}")
        
        if event_type == 'assistantResponseEvent':
            content = event['payload'].get('content', '')
            if content:
                text_content.append(content)
    
    # Validate
    full_text = ''.join(text_content)
    assert full_text == 'Hello world!', f"Expected 'Hello world!', got '{full_text}'"
    assert usage_data['input'] == 100
    assert usage_data['output'] == 50
    
    print(f"\nReconstructed text: '{full_text}'")
    print(f"Usage: {usage_data['input']} input, {usage_data['output']} output tokens")
    
    print("\n✓ Test passed!")


def test_tool_use_response():
    """Test 6: Tool use response translation"""
    print("\n" + "="*60)
    print("Test 6: Tool Use Response")
    print("="*60)
    
    # Simulate Anthropic tool use response
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 150}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'id': 'tool_123', 'name': 'readFile'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ': "test.py"}'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 30}},
        {'type': 'message_stop'}
    ]
    
    # Translate to AWS Event Stream
    aws_stream = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    
    print(f"\nGenerated {len(aws_stream)} bytes of AWS Event Stream")
    
    # Decode and validate
    events = decode_event_stream(aws_stream)
    print(f"\nDecoded {len(events)} events:")
    
    tool_events = []
    for i, event in enumerate(events, 1):
        event_type = event['headers'].get(':event-type')
        print(f"  {i}. {event_type}")
        
        if event_type == 'toolUseEvent':
            tool_events.append(event['payload'])
    
    # Validate
    assert len(tool_events) > 0, "No tool use events found"
    
    # Reconstruct tool input
    tool_input = ''.join(e.get('input', '') for e in tool_events)
    print(f"\nTool: {tool_events[0].get('name')}")
    print(f"Tool ID: {tool_events[0].get('toolUseId')}")
    print(f"Input: {tool_input}")
    
    assert tool_events[0]['name'] == 'readFile'
    assert tool_events[0]['toolUseId'] == 'tool_123'
    assert '{"path": "test.py"}' in tool_input
    
    print("\n✓ Test passed!")


def run_all_tests():
    """Run all translation tests"""
    print("\n" + "="*60)
    print("Anthropic Translation Tests")
    print("="*60)
    
    tests = [
        test_simple_message,
        test_message_with_history,
        test_message_with_tools,
        test_message_with_tool_results,
        test_response_translation,
        test_tool_use_response
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
