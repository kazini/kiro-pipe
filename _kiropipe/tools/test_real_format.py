#!/usr/bin/env python3
"""
Test with real AWS Q format from captured traffic
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.request_translator import translate_to_anthropic


def test_tool_result_format():
    """Test with real tool result format"""
    print("\n" + "="*60)
    print("Test: Real Tool Result Format")
    print("="*60 + "\n")
    
    # Real format from your example
    aws_request = {
        "conversationState": {
            "agentContinuationId": "787cbf74-9618-4f92-8f32-fe71e4e985c7",
            "agentTaskType": "vibe",
            "chatTriggerType": "MANUAL",
            "conversationId": "903ff0ee-694a-47db-837e-6c0674ca6efc",
            "currentMessage": {
                "userInputMessage": {
                    "content": "",
                    "modelId": "auto",
                    "origin": "AI_EDITOR",
                    "userInputMessageContext": {
                        "toolResults": [
                            {
                                "content": [
                                    {"text": "Replaced text in kiropipe.py"}
                                ],
                                "status": "success",
                                "toolUseId": "tooluse_ieWjQG5fHtB6TbuGCOJ1PK"
                            }
                        ],
                        "tools": [
                            {
                                "toolSpecification": {
                                    "description": "Execute shell command",
                                    "name": "executePwsh",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "command": {"type": "string"}
                                        },
                                        "required": ["command"]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
    
    # Translate
    anthropic_req = translate_to_anthropic(aws_request)
    
    print("✓ Translation successful\n")
    print("Anthropic Request:")
    print(json.dumps(anthropic_req, indent=2))
    
    # Verify structure
    assert 'messages' in anthropic_req
    assert len(anthropic_req['messages']) == 1
    
    message = anthropic_req['messages'][0]
    assert message['role'] == 'user'
    assert isinstance(message['content'], list)
    
    # Check tool result
    tool_result = None
    for item in message['content']:
        if item.get('type') == 'tool_result':
            tool_result = item
            break
    
    assert tool_result is not None
    assert tool_result['tool_use_id'] == 'tooluse_ieWjQG5fHtB6TbuGCOJ1PK'
    assert 'Replaced text in kiropipe.py' in tool_result['content']
    
    # Check tools
    assert 'tools' in anthropic_req
    assert len(anthropic_req['tools']) == 1
    assert anthropic_req['tools'][0]['name'] == 'executePwsh'
    
    print("\n✓ All assertions passed!")
    return True


def test_simple_message():
    """Test simple message without tools"""
    print("\n" + "="*60)
    print("Test: Simple Message")
    print("="*60 + "\n")
    
    aws_request = {
        "conversationState": {
            "conversationId": "test-123",
            "currentMessage": {
                "userInputMessage": {
                    "content": "Hello, how are you?",
                    "modelId": "auto"
                }
            }
        }
    }
    
    anthropic_req = translate_to_anthropic(aws_request)
    
    print("✓ Translation successful\n")
    print("Anthropic Request:")
    print(json.dumps(anthropic_req, indent=2))
    
    assert anthropic_req['messages'][0]['content'] == "Hello, how are you?"
    
    print("\n✓ All assertions passed!")
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Real Format Translation Tests")
    print("="*60)
    
    tests = [
        ("Simple Message", test_simple_message),
        ("Tool Result Format", test_tool_result_format),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60 + "\n")
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Format handling is correct.")
    else:
        print("\n✗ Some tests failed.")
    
    print()
