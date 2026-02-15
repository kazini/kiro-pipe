#!/usr/bin/env python3
"""
Inject to Kiro - Prepare a message to be injected into Kiro
This creates a response file that kiropipe.py will inject on the next request
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


def text_to_anthropic_stream(text: str, include_tool: bool = False):
    """Convert text to Anthropic streaming format"""
    events = []
    
    # Message start
    events.append({
        'type': 'message_start',
        'message': {'usage': {'input_tokens': 100}}
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
            'delta': {'type': 'text_delta', 'text': chunk}
        })
    
    # Content block stop
    events.append({'type': 'content_block_stop'})
    
    # Optional tool call
    if include_tool:
        events.append({
            'type': 'content_block_start',
            'content_block': {
                'type': 'tool_use',
                'id': 'tooluse_injected_123',
                'name': 'readFile'
            }
        })
        
        events.append({
            'type': 'content_block_delta',
            'index': 0,
            'delta': {'type': 'input_json_delta', 'partial_json': '{"path"'}
        })
        
        events.append({
            'type': 'content_block_delta',
            'index': 0,
            'delta': {'type': 'input_json_delta', 'partial_json': ': "test.py"}'}
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
    """Convert Anthropic events to AWS Event Stream binary"""
    from engine.response_translator import translate_anthropic_stream
    
    chunks = []
    for chunk in translate_anthropic_stream(iter(anthropic_events)):
        chunks.append(chunk)
    
    return b''.join(chunks)


def inject_to_kiro(text: str, include_tool: bool = False):
    """
    Prepare a message to be injected into Kiro
    
    Args:
        text: The text to inject
        include_tool: Whether to include a tool call
    """
    print(f"\n{'='*60}")
    print("Inject to Kiro")
    print(f"{'='*60}")
    print(f"Message: {text}")
    print(f"Include tool: {include_tool}")
    print(f"{'='*60}\n")
    
    # Step 1: Convert to Anthropic format
    print("Step 1: Converting to Anthropic format...")
    anthropic_events = text_to_anthropic_stream(text, include_tool)
    print(f"  ✓ Generated {len(anthropic_events)} events")
    
    # Step 2: Convert to AWS Event Stream
    print("\nStep 2: Converting to AWS Event Stream...")
    aws_binary = anthropic_to_aws_stream(anthropic_events)
    print(f"  ✓ Generated {len(aws_binary)} bytes")
    
    # Step 3: Add to injection queue
    import base64
    
    queue_file = Path(__file__).parent.parent / 'debug_logs' / '.injection_queue.json'
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing queue or create new
    if queue_file.exists():
        try:
            queue = json.loads(queue_file.read_text())
        except:
            queue = []
    else:
        queue = []
    
    # Add new injection to queue
    injection = {
        'text': text,
        'include_tool': include_tool,
        'size': len(aws_binary),
        'events': len(anthropic_events),
        'binary': base64.b64encode(aws_binary).decode('utf-8')
    }
    queue.append(injection)
    
    # Save queue
    queue_file.write_text(json.dumps(queue, indent=2))
    
    print(f"\n  ✓ Added to injection queue: {queue_file}")
    print(f"  ✓ Queue position: #{len(queue)}")
    print(f"  ✓ Total in queue: {len(queue)}")
    
    # Step 4: Instructions
    print(f"\n{'='*60}")
    print("Next Steps:")
    print(f"{'='*60}")
    print("\n1. Launch Kiro (if not already running):")
    print("   python kiropipe.py")
    print("\n2. Send ANY message in Kiro")
    print("   (kiropipe will automatically inject your prepared response)")
    print("\n3. Your message will appear in Kiro:")
    print(f"   \"{text}\"")
    
    if include_tool:
        print("\n   Plus a tool call: readFile(test.py)")
    
    if len(queue) > 1:
        print(f"\nNote: {len(queue)} messages in queue.")
        print("They will be injected in order on the next requests.")
    
    print(f"\n{'='*60}")
    print("✓ Injection queued!")
    print(f"{'='*60}\n")
    
    return True


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\nUsage: python inject_to_kiro.py \"Your message here\" [--tool]")
        print("\nPrepare a message to be injected into Kiro")
        print("\nExamples:")
        print("  python _kiropipe/tools/inject_to_kiro.py \"Hello from injection!\"")
        print("  python _kiropipe/tools/inject_to_kiro.py \"Read the file\" --tool")
        print("\nHow it works:")
        print("  1. Converts your text to AWS Event Stream binary")
        print("  2. Saves to _kiropipe/debug_logs/.inject_response")
        print("  3. kiropipe.py reads this file and injects on next request")
        print("\nPrerequisites:")
        print("  - kiropipe.py must have INJECT_MODE = True")
        print("  - Launch Kiro via: python kiropipe.py")
        print("  - Send any message in Kiro to trigger injection")
        print()
        return 1
    
    text = sys.argv[1]
    include_tool = '--tool' in sys.argv
    
    inject_to_kiro(text, include_tool)
    return 0


if __name__ == '__main__':
    sys.exit(main())
