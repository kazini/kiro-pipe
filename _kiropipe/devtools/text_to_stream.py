#!/usr/bin/env python3
"""
Text to Stream - Convert text to AWS Event Stream format
Takes a simple text string and converts it through the full pipeline:
  Text → Anthropic format → AWS Event Stream binary

This simulates what the bridge does when converting LLM responses.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.event_stream_encoder import (
    encode_text_chunk,
    encode_tool_use_chunk,
    encode_metering,
    encode_context_usage
)
from engine.decode_event_stream import decode_event_stream


def text_to_anthropic_stream(text: str, include_tool: bool = False):
    """
    Convert text to Anthropic streaming format
    
    Args:
        text: The text to convert
        include_tool: Whether to include a tool call
    
    Returns:
        List of Anthropic event dicts
    """
    events = []
    
    # Message start
    events.append({
        'type': 'message_start',
        'message': {
            'usage': {'input_tokens': 100}
        }
    })
    
    # Content block start
    events.append({
        'type': 'content_block_start',
        'content_block': {'type': 'text'}
    })
    
    # Split text into chunks (simulate streaming)
    words = text.split()
    for i, word in enumerate(words):
        chunk = word + (' ' if i < len(words) - 1 else '')
        events.append({
            'type': 'content_block_delta',
            'delta': {
                'type': 'text_delta',
                'text': chunk
            }
        })
    
    # Content block stop
    events.append({'type': 'content_block_stop'})
    
    # Optional tool call
    if include_tool:
        events.append({
            'type': 'content_block_start',
            'content_block': {
                'type': 'tool_use',
                'id': 'tooluse_test_123',
                'name': 'readFile'
            }
        })
        
        events.append({
            'type': 'content_block_delta',
            'index': 0,
            'delta': {
                'type': 'input_json_delta',
                'partial_json': '{"path"'
            }
        })
        
        events.append({
            'type': 'content_block_delta',
            'index': 0,
            'delta': {
                'type': 'input_json_delta',
                'partial_json': ': "test.py"}'
            }
        })
        
        events.append({'type': 'content_block_stop'})
    
    # Message delta with usage
    events.append({
        'type': 'message_delta',
        'usage': {'output_tokens': len(words)}
    })
    
    # Message stop
    events.append({'type': 'message_stop'})
    
    return events


def anthropic_to_aws_stream(anthropic_events: list) -> bytes:
    """
    Convert Anthropic events to AWS Event Stream binary
    
    Args:
        anthropic_events: List of Anthropic event dicts
    
    Returns:
        Binary AWS Event Stream data
    """
    from engine.response_translator import translate_anthropic_stream
    
    chunks = []
    for chunk in translate_anthropic_stream(iter(anthropic_events)):
        chunks.append(chunk)
    
    return b''.join(chunks)


def text_to_stream(text: str, include_tool: bool = False, output_file: str = None):
    """
    Convert text to AWS Event Stream format
    
    Args:
        text: The text to convert
        include_tool: Whether to include a tool call
        output_file: Optional file to save binary output
    """
    print(f"\n{'='*60}")
    print("Text to AWS Event Stream Converter")
    print(f"{'='*60}")
    print(f"Input text: {text}")
    print(f"Include tool: {include_tool}")
    print(f"{'='*60}\n")
    
    # Step 1: Convert to Anthropic format
    print("Step 1: Converting to Anthropic streaming format...")
    anthropic_events = text_to_anthropic_stream(text, include_tool)
    print(f"  ✓ Generated {len(anthropic_events)} Anthropic events")
    
    # Show Anthropic format
    print("\nAnthropic Events:")
    print("-" * 60)
    for i, event in enumerate(anthropic_events, 1):
        event_type = event.get('type', 'unknown')
        print(f"  {i}. {event_type}")
        if event_type == 'content_block_delta':
            delta = event.get('delta', {})
            if delta.get('type') == 'text_delta':
                print(f"     Text: {delta.get('text', '')!r}")
    print()
    
    # Step 2: Convert to AWS Event Stream
    print("Step 2: Converting to AWS Event Stream binary...")
    aws_binary = anthropic_to_aws_stream(anthropic_events)
    print(f"  ✓ Generated {len(aws_binary)} bytes of binary data")
    print(f"  ✓ First 100 bytes (hex): {aws_binary[:100].hex()}")
    print()
    
    # Step 3: Verify by decoding
    print("Step 3: Verifying by decoding...")
    decoded_events = decode_event_stream(aws_binary)
    print(f"  ✓ Decoded {len(decoded_events)} AWS events")
    
    # Show decoded events
    print("\nAWS Event Stream Events:")
    print("-" * 60)
    for i, event in enumerate(decoded_events, 1):
        event_type = event['headers'].get(':event-type', 'unknown')
        payload = event['payload']
        print(f"  {i}. {event_type}")
        if event_type == 'assistantResponseEvent' and isinstance(payload, dict):
            content = payload.get('content', '')
            if content:
                print(f"     Content: {content!r}")
        elif event_type == 'toolUseEvent' and isinstance(payload, dict):
            tool_name = payload.get('name', '')
            print(f"     Tool: {tool_name}")
    print()
    
    # Step 4: Reconstruct and display
    print("Step 4: Reconstructing message...")
    reconstructed_text = ""
    tool_calls = []
    
    for event in decoded_events:
        event_type = event['headers'].get(':event-type', '')
        payload = event['payload']
        
        if event_type == 'assistantResponseEvent':
            if isinstance(payload, dict) and 'content' in payload:
                reconstructed_text += payload['content']
        
        elif event_type == 'toolUseEvent':
            if isinstance(payload, dict):
                tool_name = payload.get('name', '')
                tool_id = payload.get('toolUseId', '')
                input_chunk = payload.get('input', '')
                
                # Find or create tool call
                tool_call = next((t for t in tool_calls if t['id'] == tool_id), None)
                if tool_call is None:
                    tool_call = {'name': tool_name, 'id': tool_id, 'input': ''}
                    tool_calls.append(tool_call)
                
                if input_chunk:
                    tool_call['input'] += input_chunk
    
    print(f"  ✓ Reconstructed text: {reconstructed_text!r}")
    if tool_calls:
        for tool in tool_calls:
            print(f"  ✓ Tool call: {tool['name']} with input: {tool['input']}")
    print()
    
    # Verify match
    if reconstructed_text == text:
        print("✓ Verification successful! Text matches original.")
    else:
        print("✗ Warning: Reconstructed text doesn't match original")
        print(f"  Original: {text!r}")
        print(f"  Reconstructed: {reconstructed_text!r}")
    
    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(aws_binary)
        print(f"\n✓ Binary saved to: {output_file}")
    
    print(f"\n{'='*60}")
    print("✓ Conversion complete!")
    print(f"{'='*60}\n")
    
    return aws_binary


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\nUsage: python text_to_stream.py \"Your text here\" [--tool] [--output file.bin]")
        print("\nConvert text to AWS Event Stream format (simulates bridge output)")
        print("\nExamples:")
        print("  python _kiropipe/tools/text_to_stream.py \"Hello, world!\"")
        print("  python _kiropipe/tools/text_to_stream.py \"Read the file\" --tool")
        print("  python _kiropipe/tools/text_to_stream.py \"Test\" --output test.bin")
        print("\nOptions:")
        print("  --tool    Include a tool call (readFile)")
        print("  --output  Save binary to file")
        print("\nThis tests the complete conversion pipeline:")
        print("  Text → Anthropic format → AWS Event Stream binary")
        print()
        return 1
    
    text = sys.argv[1]
    include_tool = '--tool' in sys.argv
    
    output_file = None
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    text_to_stream(text, include_tool, output_file)
    return 0


if __name__ == '__main__':
    sys.exit(main())
