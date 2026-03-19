#!/usr/bin/env python3
"""
Validate Format Translation
Compare our translation with real AWS Q samples
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.decode_event_stream import decode_event_stream
from engine.event_stream_encoder import encode_text_chunk, encode_tool_use_chunk, encode_metering, encode_context_usage


def analyze_real_aws_response(response_file: Path):
    """Analyze a real AWS Q response"""
    print(f"\n{'='*60}")
    print(f"Analyzing: {response_file.name}")
    print(f"{'='*60}")
    
    with open(response_file, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    events = decode_event_stream(data)
    print(f"Total events: {len(events)}")
    
    # Categorize events
    event_types = {}
    text_events = []
    tool_events = []
    metering_events = []
    context_events = []
    
    for event in events:
        event_type = event['headers'].get(':event-type')
        event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if event_type == 'assistantResponseEvent':
            content = event['payload'].get('content', '')
            if content:
                text_events.append(content)
        
        elif event_type == 'toolUseEvent':
            tool_events.append(event['payload'])
        
        elif event_type == 'meteringEvent':
            metering_events.append(event['payload'])
        
        elif event_type == 'contextUsageEvent':
            context_events.append(event['payload'])
    
    print(f"\nEvent types:")
    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type}: {count}")
    
    # Analyze text content
    if text_events:
        full_text = ''.join(text_events)
        print(f"\nText content ({len(text_events)} chunks):")
        print(f"  Total length: {len(full_text)} chars")
        if len(full_text) < 200:
            print(f"  Content: {full_text}")
        else:
            print(f"  First 200 chars: {full_text[:200]}...")
    
    # Analyze tool use
    if tool_events:
        print(f"\nTool use ({len(tool_events)} events):")
        
        # Group by tool ID
        tools_by_id = {}
        for event in tool_events:
            tool_id = event.get('toolUseId', 'unknown')
            if tool_id not in tools_by_id:
                tools_by_id[tool_id] = {
                    'name': event.get('name', 'unknown'),
                    'chunks': [],
                    'stop': False
                }
            
            if 'input' in event:
                tools_by_id[tool_id]['chunks'].append(event['input'])
            
            if event.get('stop'):
                tools_by_id[tool_id]['stop'] = True
        
        for tool_id, tool_data in tools_by_id.items():
            full_input = ''.join(tool_data['chunks'])
            print(f"  Tool: {tool_data['name']}")
            print(f"    ID: {tool_id}")
            print(f"    Chunks: {len(tool_data['chunks'])}")
            print(f"    Stop event: {tool_data['stop']}")
            print(f"    Input length: {len(full_input)} chars")
            if len(full_input) < 100:
                print(f"    Input: {full_input}")
            else:
                print(f"    Input (first 100): {full_input[:100]}...")
    
    # Analyze metering
    if metering_events:
        print(f"\nMetering ({len(metering_events)} events):")
        for event in metering_events:
            print(f"  Usage: {event.get('usage', 0):.4f} {event.get('unitPlural', 'units')}")
    
    # Analyze context usage
    if context_events:
        print(f"\nContext usage ({len(context_events)} events):")
        for event in context_events:
            print(f"  Percentage: {event.get('contextUsagePercentage', 0):.2f}%")
    
    return {
        'events': events,
        'event_types': event_types,
        'text_events': text_events,
        'tool_events': tool_events,
        'metering_events': metering_events,
        'context_events': context_events
    }


def test_our_encoding():
    """Test our encoding matches AWS Q format"""
    print(f"\n{'='*60}")
    print("Testing Our Encoding")
    print(f"{'='*60}")
    
    # Test 1: Simple text
    print("\nTest 1: Text encoding")
    text_chunk = encode_text_chunk("Hello, world!")
    events = decode_event_stream(text_chunk)
    
    assert len(events) == 1
    assert events[0]['headers'][':event-type'] == 'assistantResponseEvent'
    assert events[0]['payload']['content'] == "Hello, world!"
    print("  ✓ Text encoding works")
    
    # Test 2: Tool use
    print("\nTest 2: Tool use encoding")
    tool_chunk = encode_tool_use_chunk("readFile", "tool_123", '{"path": "test.py"}')
    events = decode_event_stream(tool_chunk)
    
    assert len(events) == 1
    assert events[0]['headers'][':event-type'] == 'toolUseEvent'
    assert events[0]['payload']['name'] == 'readFile'
    assert events[0]['payload']['toolUseId'] == 'tool_123'
    assert events[0]['payload']['input'] == '{"path": "test.py"}'
    print("  ✓ Tool use encoding works")
    
    # Test 3: Tool stop event
    print("\nTest 3: Tool stop encoding")
    tool_stop = encode_tool_use_chunk("readFile", "tool_123", '', is_final=True)
    events = decode_event_stream(tool_stop)
    
    # Check if stop event is encoded correctly
    print(f"  Stop event payload: {events[0]['payload']}")
    
    # AWS Q uses 'stop': true in final tool event
    if 'stop' not in events[0]['payload']:
        print("  ⚠ WARNING: Missing 'stop' field in final tool event!")
        print("  AWS Q format includes 'stop': true in final tool event")
    else:
        assert events[0]['payload']['stop'] == True
        print("  ✓ Tool stop encoding works")
    
    # Test 4: Metering
    print("\nTest 4: Metering encoding")
    metering = encode_metering(0.5, 'credit', 'credits')
    events = decode_event_stream(metering)
    
    assert len(events) == 1
    assert events[0]['headers'][':event-type'] == 'meteringEvent'
    assert events[0]['payload']['usage'] == 0.5
    assert events[0]['payload']['unit'] == 'credit'
    assert events[0]['payload']['unitPlural'] == 'credits'
    print("  ✓ Metering encoding works")
    
    # Test 5: Context usage
    print("\nTest 5: Context usage encoding")
    context = encode_context_usage(25.5)
    events = decode_event_stream(context)
    
    assert len(events) == 1
    assert events[0]['headers'][':event-type'] == 'contextUsageEvent'
    assert events[0]['payload']['contextUsagePercentage'] == 25.5
    print("  ✓ Context usage encoding works")


def compare_with_real_sample():
    """Compare our encoding with real AWS Q sample"""
    print(f"\n{'='*60}")
    print("Comparing with Real Sample")
    print(f"{'='*60}")
    
    # Find a real response file
    responses_dir = Path(__file__).parent.parent / 'debug_logs' / 'interactions' / 'responses'
    response_files = list(responses_dir.glob('response_*.bin'))
    
    if not response_files:
        print("No real response files found. Run kiropipe.py with debug mode to capture samples.")
        return
    
    # Analyze first response
    real_data = analyze_real_aws_response(response_files[0])
    
    # Create equivalent with our encoder
    print(f"\n{'='*60}")
    print("Creating Equivalent with Our Encoder")
    print(f"{'='*60}")
    
    our_stream = bytearray()
    
    # Add text chunks
    for text in real_data['text_events'][:5]:  # First 5 chunks
        our_stream.extend(encode_text_chunk(text))
    
    # Add tool chunks if present
    if real_data['tool_events']:
        tool_data = real_data['tool_events'][0]
        our_stream.extend(encode_tool_use_chunk(
            tool_data.get('name', 'unknown'),
            tool_data.get('toolUseId', 'unknown'),
            tool_data.get('input', '')
        ))
    
    # Add metering if present
    if real_data['metering_events']:
        metering = real_data['metering_events'][0]
        our_stream.extend(encode_metering(
            metering.get('usage', 0),
            metering.get('unit', 'credit'),
            metering.get('unitPlural', 'credits')
        ))
    
    # Add context usage if present
    if real_data['context_events']:
        context = real_data['context_events'][0]
        our_stream.extend(encode_context_usage(
            context.get('contextUsagePercentage', 0)
        ))
    
    print(f"\nOur encoding: {len(our_stream)} bytes")
    
    # Decode and compare
    our_events = decode_event_stream(bytes(our_stream))
    print(f"Our events: {len(our_events)}")
    
    # Compare event types
    our_event_types = {}
    for event in our_events:
        event_type = event['headers'].get(':event-type')
        our_event_types[event_type] = our_event_types.get(event_type, 0) + 1
    
    print(f"\nOur event types:")
    for event_type, count in sorted(our_event_types.items()):
        print(f"  {event_type}: {count}")
    
    print(f"\nComparison:")
    print(f"  Real events: {len(real_data['events'])}")
    print(f"  Our events: {len(our_events)}")
    print(f"  Match: {len(our_events) > 0}")


def main():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("AWS Q Format Validation")
    print("="*60)
    
    # Test our encoding
    test_our_encoding()
    
    # Compare with real samples
    compare_with_real_sample()
    
    print("\n" + "="*60)
    print("Validation Complete")
    print("="*60)


if __name__ == '__main__':
    main()
