#!/usr/bin/env python3
"""
Test Anthropic → AWS Translation
Tests the response translator with simulated Anthropic events
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.response_translator import translate_anthropic_stream
from engine.decode_event_stream import decode_event_stream


def test_simple_text():
    """Test simple text response translation"""
    print("\n" + "="*60)
    print("Test 1: Simple Text Response")
    print("="*60)
    
    # Simulate Anthropic streaming events
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 100}}},
        {'type': 'content_block_start', 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Hello'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': ' from'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': ' Anthropic!'}},
        {'type': 'content_block_stop'},
        {'type': 'message_delta', 'usage': {'output_tokens': 50}},
        {'type': 'message_stop'}
    ]
    
    # Translate to AWS format
    aws_binary = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    
    print(f"✓ Generated {len(aws_binary)} bytes of AWS Event Stream data")
    
    # Decode and verify
    events = decode_event_stream(aws_binary)
    print(f"✓ Decoded {len(events)} events")
    
    # Extract text
    text_content = ""
    for event in events:
        event_type = event['headers'].get(':event-type')
        payload = event['payload']
        
        if event_type == 'assistantResponseEvent':
            if isinstance(payload, dict) and 'content' in payload:
                text_content += payload['content']
        
        print(f"  - {event_type}: {payload}")
    
    print(f"\n✓ Reconstructed text: '{text_content}'")
    
    expected = "Hello from Anthropic!"
    if text_content == expected:
        print(f"✓ Text matches expected output!")
        return True
    else:
        print(f"✗ Text mismatch!")
        print(f"  Expected: '{expected}'")
        print(f"  Got: '{text_content}'")
        return False


def test_tool_use():
    """Test tool use response translation"""
    print("\n" + "="*60)
    print("Test 2: Tool Use Response")
    print("="*60)
    
    # Simulate Anthropic tool use events
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 150}}},
        {'type': 'content_block_start', 'content_block': {'type': 'tool_use', 'id': 'tool_abc123', 'name': 'readFile'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ': "test.py"}'}},
        {'type': 'content_block_stop'},
        {'type': 'message_delta', 'usage': {'output_tokens': 30}},
        {'type': 'message_stop'}
    ]
    
    # Translate to AWS format
    aws_binary = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    
    print(f"✓ Generated {len(aws_binary)} bytes of AWS Event Stream data")
    
    # Decode and verify
    events = decode_event_stream(aws_binary)
    print(f"✓ Decoded {len(events)} events")
    
    # Extract tool calls
    tool_calls = {}
    for event in events:
        event_type = event['headers'].get(':event-type')
        payload = event['payload']
        
        if event_type == 'toolUseEvent':
            if isinstance(payload, dict):
                tool_id = payload.get('toolUseId', '')
                tool_name = payload.get('name', '')
                input_chunk = payload.get('input', '')
                
                if tool_id not in tool_calls:
                    tool_calls[tool_id] = {'name': tool_name, 'input': ''}
                
                if input_chunk:
                    tool_calls[tool_id]['input'] += input_chunk
        
        print(f"  - {event_type}: {payload}")
    
    print(f"\n✓ Tool calls: {tool_calls}")
    
    if 'tool_abc123' in tool_calls:
        tool = tool_calls['tool_abc123']
        if tool['name'] == 'readFile' and '{"path": "test.py"}' in tool['input']:
            print(f"✓ Tool call matches expected output!")
            return True
    
    print(f"✗ Tool call mismatch!")
    return False


def test_mixed_content():
    """Test mixed text and tool use"""
    print("\n" + "="*60)
    print("Test 3: Mixed Text and Tool Use")
    print("="*60)
    
    # Simulate mixed content
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 200}}},
        {'type': 'content_block_start', 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Let me read that file for you.'}},
        {'type': 'content_block_stop'},
        {'type': 'content_block_start', 'content_block': {'type': 'tool_use', 'id': 'tool_xyz789', 'name': 'readFile'}},
        {'type': 'content_block_delta', 'index': 1, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path": "data.json"}'}},
        {'type': 'content_block_stop'},
        {'type': 'message_delta', 'usage': {'output_tokens': 80}},
        {'type': 'message_stop'}
    ]
    
    # Translate to AWS format
    aws_binary = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    
    print(f"✓ Generated {len(aws_binary)} bytes of AWS Event Stream data")
    
    # Decode and verify
    events = decode_event_stream(aws_binary)
    print(f"✓ Decoded {len(events)} events")
    
    text_content = ""
    tool_calls = {}
    
    for event in events:
        event_type = event['headers'].get(':event-type')
        payload = event['payload']
        
        if event_type == 'assistantResponseEvent':
            if isinstance(payload, dict) and 'content' in payload:
                text_content += payload['content']
        
        elif event_type == 'toolUseEvent':
            if isinstance(payload, dict):
                tool_id = payload.get('toolUseId', '')
                tool_name = payload.get('name', '')
                input_chunk = payload.get('input', '')
                
                if tool_id not in tool_calls:
                    tool_calls[tool_id] = {'name': tool_name, 'input': ''}
                
                if input_chunk:
                    tool_calls[tool_id]['input'] += input_chunk
        
        print(f"  - {event_type}: {payload}")
    
    print(f"\n✓ Text: '{text_content}'")
    print(f"✓ Tool calls: {tool_calls}")
    
    has_text = "Let me read that file for you." in text_content
    has_tool = 'tool_xyz789' in tool_calls
    
    if has_text and has_tool:
        print(f"✓ Mixed content matches expected output!")
        return True
    else:
        print(f"✗ Mixed content mismatch!")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Anthropic → AWS Translation Tests")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Simple Text", test_simple_text()))
    results.append(("Tool Use", test_tool_use()))
    results.append(("Mixed Content", test_mixed_content()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
