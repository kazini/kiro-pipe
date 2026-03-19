#!/usr/bin/env python3
"""
Test OpenAI Translation
Comprehensive tests for AWS Q ↔ OpenAI format translation
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.request_translator import translate_to_openai, extract_tools, extract_tool_results
from engine.response_translator import translate_openai_stream
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
                    'modelId': 'gpt-4',
                    'origin': 'AI_EDITOR'
                }
            }
        }
    }
    
    openai_request = translate_to_openai(aws_request)
    
    print("\nAWS Q Request:")
    print(json.dumps(aws_request, indent=2))
    
    print("\nOpenAI Request:")
    print(json.dumps(openai_request, indent=2))
    
    # Validate
    assert openai_request['model'] == 'gpt-4'
    assert len(openai_request['messages']) == 1
    assert openai_request['messages'][0]['role'] == 'user'
    assert openai_request['messages'][0]['content'] == 'Hello, how are you?'
    assert openai_request['stream'] == True
    assert 'tools' not in openai_request
    
    print("\n✓ Test passed!")


def test_message_with_tools():
    """Test 2: User message with tool definitions"""
    print("\n" + "="*60)
    print("Test 2: Message with Tools")
    print("="*60)
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Read the file test.py',
                    'modelId': 'gpt-4',
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
    
    openai_request = translate_to_openai(aws_request)
    
    print("\nOpenAI Request:")
    print(json.dumps(openai_request, indent=2))
    
    # Validate
    assert 'tools' in openai_request
    assert len(openai_request['tools']) == 1
    
    tool = openai_request['tools'][0]
    assert tool['type'] == 'function'
    assert 'function' in tool
    assert tool['function']['name'] == 'readFile'
    assert 'description' in tool['function']
    assert 'parameters' in tool['function']
    
    print("\n✓ Test passed!")


def test_message_with_tool_results():
    """Test 3: User message with tool results"""
    print("\n" + "="*60)
    print("Test 3: Message with Tool Results")
    print("="*60)
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': '',
                    'modelId': 'gpt-4',
                    'origin': 'AI_EDITOR',
                    'userInputMessageContext': {
                        'toolResults': [
                            {
                                'toolUseId': 'call_abc123',
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
    
    openai_request = translate_to_openai(aws_request)
    
    print("\nOpenAI Request:")
    print(json.dumps(openai_request, indent=2))
    
    # Validate - OpenAI uses separate 'tool' role messages
    assert len(openai_request['messages']) >= 1
    
    # Find tool message
    tool_msg = next((m for m in openai_request['messages'] if m['role'] == 'tool'), None)
    assert tool_msg is not None, "Should have tool role message"
    assert tool_msg['tool_call_id'] == 'call_abc123'
    assert 'File contents: Hello, world!' in tool_msg['content']
    
    print("\n✓ Test passed!")


def test_response_translation():
    """Test 4: OpenAI response → AWS Event Stream"""
    print("\n" + "="*60)
    print("Test 4: Response Translation")
    print("="*60)
    
    # Simulate OpenAI streaming response
    openai_chunks = [
        {
            'choices': [
                {
                    'delta': {'content': 'Hello'},
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {'content': ' world'},
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {'content': '!'},
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {},
                    'finish_reason': 'stop'
                }
            ],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
    ]
    
    # Track usage
    usage_data = {}
    
    def usage_callback(input_tokens, output_tokens):
        usage_data['input'] = input_tokens
        usage_data['output'] = output_tokens
    
    # Translate to AWS Event Stream
    aws_stream = b''.join(translate_openai_stream(
        iter(openai_chunks),
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


def test_tool_call_response():
    """Test 5: OpenAI tool call response translation"""
    print("\n" + "="*60)
    print("Test 5: Tool Call Response")
    print("="*60)
    
    # Simulate OpenAI tool call response
    openai_chunks = [
        {
            'choices': [
                {
                    'delta': {
                        'tool_calls': [
                            {
                                'index': 0,
                                'id': 'call_abc123',
                                'type': 'function',
                                'function': {
                                    'name': 'readFile',
                                    'arguments': ''
                                }
                            }
                        ]
                    },
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {
                        'tool_calls': [
                            {
                                'index': 0,
                                'function': {
                                    'arguments': '{"path"'
                                }
                            }
                        ]
                    },
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {
                        'tool_calls': [
                            {
                                'index': 0,
                                'function': {
                                    'arguments': ': "test.py"}'
                                }
                            }
                        ]
                    },
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {},
                    'finish_reason': 'tool_calls'
                }
            ],
            'usage': {
                'prompt_tokens': 150,
                'completion_tokens': 30,
                'total_tokens': 180
            }
        }
    ]
    
    # Translate to AWS Event Stream
    aws_stream = b''.join(translate_openai_stream(iter(openai_chunks)))
    
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
    
    # Check for stop event
    has_stop = any(e.get('stop') for e in tool_events)
    print(f"Has stop event: {has_stop}")
    
    assert tool_events[0]['name'] == 'readFile'
    assert tool_events[0]['toolUseId'] == 'call_abc123'
    assert '{"path": "test.py"}' in tool_input
    assert has_stop == True, "Tool call should have stop event"
    
    print("\n✓ Test passed!")


def test_multiple_tool_calls():
    """Test 6: Multiple tool calls in one response"""
    print("\n" + "="*60)
    print("Test 6: Multiple Tool Calls")
    print("="*60)
    
    # Simulate OpenAI response with multiple tool calls
    openai_chunks = [
        {
            'choices': [
                {
                    'delta': {
                        'tool_calls': [
                            {
                                'index': 0,
                                'id': 'call_1',
                                'type': 'function',
                                'function': {
                                    'name': 'readFile',
                                    'arguments': '{"path": "a.txt"}'
                                }
                            }
                        ]
                    },
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {
                        'tool_calls': [
                            {
                                'index': 1,
                                'id': 'call_2',
                                'type': 'function',
                                'function': {
                                    'name': 'readFile',
                                    'arguments': '{"path": "b.txt"}'
                                }
                            }
                        ]
                    },
                    'finish_reason': None
                }
            ]
        },
        {
            'choices': [
                {
                    'delta': {},
                    'finish_reason': 'tool_calls'
                }
            ]
        }
    ]
    
    # Translate to AWS Event Stream
    aws_stream = b''.join(translate_openai_stream(iter(openai_chunks)))
    
    events = decode_event_stream(aws_stream)
    tool_events = [e for e in events if e['headers'].get(':event-type') == 'toolUseEvent']
    
    print(f"\nTotal events: {len(events)}")
    print(f"Tool events: {len(tool_events)}")
    
    # Group by tool ID
    tools_by_id = {}
    for event in tool_events:
        tool_id = event['payload'].get('toolUseId')
        if tool_id not in tools_by_id:
            tools_by_id[tool_id] = []
        tools_by_id[tool_id].append(event['payload'])
    
    print(f"\nUnique tools: {len(tools_by_id)}")
    
    for tool_id, events in tools_by_id.items():
        tool_name = events[0].get('name')
        tool_input = ''.join(e.get('input', '') for e in events)
        has_stop = any(e.get('stop') for e in events)
        
        print(f"  {tool_id}: {tool_name}")
        print(f"    Input: {tool_input}")
        print(f"    Stop: {has_stop}")
    
    # Validate
    assert len(tools_by_id) == 2, "Should have 2 tool calls"
    assert 'call_1' in tools_by_id
    assert 'call_2' in tools_by_id
    
    print("\n✓ Test passed!")


def run_all_tests():
    """Run all OpenAI translation tests"""
    print("\n" + "="*60)
    print("OpenAI Translation Tests")
    print("="*60)
    
    tests = [
        test_simple_message,
        test_message_with_tools,
        test_message_with_tool_results,
        test_response_translation,
        test_tool_call_response,
        test_multiple_tool_calls
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
