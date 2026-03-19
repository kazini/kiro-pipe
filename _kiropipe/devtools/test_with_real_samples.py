#!/usr/bin/env python3
"""
Test with Real AWS Q Samples
Validate translation using actual captured traffic
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.request_translator import translate_to_anthropic
from engine.response_translator import translate_anthropic_stream
from engine.decode_event_stream import decode_event_stream


def load_sample_request(request_file: Path):
    """Load a sample AWS Q request"""
    with open(request_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract the body (which contains the actual request)
    if 'body' in data:
        if isinstance(data['body'], str):
            return json.loads(data['body'])
        return data['body']
    
    return data


def test_request_translation():
    """Test request translation with real samples"""
    print("\n" + "="*60)
    print("Testing Request Translation with Real Samples")
    print("="*60)
    
    # Find sample requests
    samples_dir = Path(__file__).parent.parent.parent / 'samples' / 'post'
    request_files = sorted(samples_dir.glob('request_*.json'))
    
    if not request_files:
        print("No sample request files found in samples/post/")
        return False
    
    print(f"\nFound {len(request_files)} sample requests")
    
    passed = 0
    failed = 0
    
    for request_file in request_files[:3]:  # Test first 3
        print(f"\n{'='*60}")
        print(f"Testing: {request_file.name}")
        print(f"{'='*60}")
        
        try:
            # Load AWS Q request
            aws_request = load_sample_request(request_file)
            
            # Extract key info
            conv_state = aws_request.get('conversationState', {})
            current_msg = conv_state.get('currentMessage', {})
            user_input = current_msg.get('userInputMessage', {})
            
            content = user_input.get('content', '')
            model_id = user_input.get('modelId', 'unknown')
            context = user_input.get('userInputMessageContext', {})
            tools = context.get('tools', [])
            tool_results = context.get('toolResults', [])
            history = conv_state.get('history', [])
            
            print(f"\nAWS Q Request Info:")
            print(f"  Model: {model_id}")
            print(f"  Content length: {len(content)} chars")
            print(f"  History items: {len(history)}")
            print(f"  Tools: {len(tools)}")
            print(f"  Tool results: {len(tool_results)}")
            
            # Translate to Anthropic
            anthropic_request = translate_to_anthropic(aws_request, model=model_id)
            
            print(f"\nAntropic Request:")
            print(f"  Model: {anthropic_request['model']}")
            print(f"  Messages: {len(anthropic_request['messages'])}")
            print(f"  Stream: {anthropic_request['stream']}")
            
            if 'tools' in anthropic_request:
                print(f"  Tools: {len(anthropic_request['tools'])}")
            
            # Validate structure
            assert 'model' in anthropic_request
            assert 'messages' in anthropic_request
            assert 'stream' in anthropic_request
            assert anthropic_request['stream'] == True
            assert len(anthropic_request['messages']) > 0
            
            # Validate messages
            for msg in anthropic_request['messages']:
                assert 'role' in msg
                assert msg['role'] in ['user', 'assistant']
                assert 'content' in msg
            
            # If tools present, validate them
            if tools:
                assert 'tools' in anthropic_request
                for tool in anthropic_request['tools']:
                    assert 'name' in tool
                    assert 'description' in tool or 'input_schema' in tool
            
            # If tool results present, check message format
            if tool_results:
                # Last message should be user with tool_result content
                last_msg = anthropic_request['messages'][-1]
                assert last_msg['role'] == 'user'
                
                if isinstance(last_msg['content'], list):
                    # Check for tool_result type
                    has_tool_result = any(
                        isinstance(c, dict) and c.get('type') == 'tool_result'
                        for c in last_msg['content']
                    )
                    assert has_tool_result, "Tool results should be in message content"
            
            print(f"\n✓ Translation valid")
            passed += 1
            
        except Exception as e:
            print(f"\n✗ Translation failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Request Translation Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    return failed == 0


def test_response_format():
    """Test response format matches AWS Q"""
    print("\n" + "="*60)
    print("Testing Response Format")
    print("="*60)
    
    # Load a real AWS Q response
    responses_dir = Path(__file__).parent.parent / 'debug_logs' / 'interactions' / 'responses'
    response_files = list(responses_dir.glob('response_*.bin'))
    
    if not response_files:
        print("No real response files found. Run kiropipe.py with debug mode to capture samples.")
        return True  # Skip test
    
    # Analyze first response
    response_file = response_files[0]
    print(f"\nAnalyzing: {response_file.name}")
    
    with open(response_file, 'rb') as f:
        real_data = f.read()
    
    real_events = decode_event_stream(real_data)
    print(f"Real AWS Q response: {len(real_events)} events")
    
    # Count event types
    real_event_types = {}
    for event in real_events:
        event_type = event['headers'].get(':event-type')
        real_event_types[event_type] = real_event_types.get(event_type, 0) + 1
    
    print(f"\nReal event types:")
    for event_type, count in sorted(real_event_types.items()):
        print(f"  {event_type}: {count}")
    
    # Simulate Anthropic response and translate
    print(f"\nSimulating Anthropic response...")
    
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 100}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': 'Hello'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': ' world'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 50}},
        {'type': 'message_stop'}
    ]
    
    our_data = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    our_events = decode_event_stream(our_data)
    
    print(f"Our translated response: {len(our_events)} events")
    
    # Count our event types
    our_event_types = {}
    for event in our_events:
        event_type = event['headers'].get(':event-type')
        our_event_types[event_type] = our_event_types.get(event_type, 0) + 1
    
    print(f"\nOur event types:")
    for event_type, count in sorted(our_event_types.items()):
        print(f"  {event_type}: {count}")
    
    # Validate structure
    print(f"\nValidating structure...")
    
    for event in our_events:
        # Check headers
        assert ':event-type' in event['headers']
        assert ':content-type' in event['headers']
        assert ':message-type' in event['headers']
        
        # Check payload
        assert isinstance(event['payload'], dict)
        
        event_type = event['headers'][':event-type']
        
        if event_type == 'assistantResponseEvent':
            assert 'content' in event['payload']
        
        elif event_type == 'toolUseEvent':
            assert 'name' in event['payload']
            assert 'toolUseId' in event['payload']
            assert 'input' in event['payload']
        
        elif event_type == 'meteringEvent':
            assert 'usage' in event['payload']
            assert 'unit' in event['payload']
            assert 'unitPlural' in event['payload']
        
        elif event_type == 'contextUsageEvent':
            assert 'contextUsagePercentage' in event['payload']
    
    print(f"✓ All events have correct structure")
    
    return True


def test_tool_use_format():
    """Test tool use format specifically"""
    print("\n" + "="*60)
    print("Testing Tool Use Format")
    print("="*60)
    
    # Simulate Anthropic tool use response
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 150}}},
        {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'id': 'tool_abc123', 'name': 'readFile'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ': "test.py"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ', "explanation"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ': "Reading file"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '}'}},
        {'type': 'content_block_stop', 'index': 0},
        {'type': 'message_delta', 'delta': {}, 'usage': {'output_tokens': 30}},
        {'type': 'message_stop'}
    ]
    
    # Translate
    aws_data = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    events = decode_event_stream(aws_data)
    
    print(f"\nGenerated {len(events)} events")
    
    # Find tool events
    tool_events = [e for e in events if e['headers'].get(':event-type') == 'toolUseEvent']
    print(f"Tool events: {len(tool_events)}")
    
    # Reconstruct tool input
    tool_input_chunks = []
    tool_name = None
    tool_id = None
    has_stop = False
    
    for event in tool_events:
        payload = event['payload']
        
        if tool_name is None:
            tool_name = payload.get('name')
            tool_id = payload.get('toolUseId')
        
        if 'input' in payload:
            tool_input_chunks.append(payload['input'])
        
        if payload.get('stop'):
            has_stop = True
    
    full_input = ''.join(tool_input_chunks)
    
    print(f"\nTool details:")
    print(f"  Name: {tool_name}")
    print(f"  ID: {tool_id}")
    print(f"  Input chunks: {len(tool_input_chunks)}")
    print(f"  Full input: {full_input}")
    print(f"  Has stop event: {has_stop}")
    
    # Validate
    assert tool_name == 'readFile'
    assert tool_id == 'tool_abc123'
    assert full_input == '{"path": "test.py", "explanation": "Reading file"}'
    assert has_stop == True, "Tool use should have stop event"
    
    print(f"\n✓ Tool use format correct")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Real Sample Validation Tests")
    print("="*60)
    
    results = []
    
    # Test request translation
    results.append(("Request Translation", test_request_translation()))
    
    # Test response format
    results.append(("Response Format", test_response_format()))
    
    # Test tool use format
    results.append(("Tool Use Format", test_tool_use_format()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
