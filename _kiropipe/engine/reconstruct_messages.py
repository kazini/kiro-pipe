#!/usr/bin/env python3
"""
Reconstruct full AI messages from decoded event streams
"""

import json
from pathlib import Path

def reconstruct_message(events):
    """Reconstruct full message from event stream (legacy function)"""
    content_chunks = []
    metadata = {
        'metering': None,
        'context_usage': None
    }
    
    for event in events:
        event_type = event['headers'].get(':event-type', '')
        payload = event['payload']
        
        if event_type == 'assistantResponseEvent':
            if isinstance(payload, dict) and 'content' in payload:
                content_chunks.append(payload['content'])
        elif event_type == 'meteringEvent':
            metadata['metering'] = payload
        elif event_type == 'contextUsageEvent':
            metadata['context_usage'] = payload
    
    full_message = ''.join(content_chunks)
    return full_message, metadata


def reconstruct_messages(events):
    """
    Reconstruct messages from event stream, including tool calls
    
    Returns list of message objects:
    - {'type': 'text', 'content': '...'}
    - {'type': 'tool_use', 'name': '...', 'id': '...', 'input': '...'}
    - {'type': 'metering', 'usage': 0.15, 'unit': 'credit'}
    - {'type': 'context_usage', 'percentage': 25.5}
    """
    messages = []
    text_chunks = []
    tool_calls = {}  # Buffer for accumulating tool call chunks
    
    for event in events:
        event_type = event['headers'].get(':event-type', '')
        payload = event['payload']
        
        if event_type == 'assistantResponseEvent':
            # Text content
            if isinstance(payload, dict) and 'content' in payload:
                text_chunks.append(payload['content'])
        
        elif event_type == 'toolUseEvent':
            # Tool call
            if isinstance(payload, dict):
                tool_id = payload.get('toolUseId', '')
                tool_name = payload.get('name', '')
                input_chunk = payload.get('input', '')
                
                # Initialize or update tool call buffer
                if tool_id not in tool_calls:
                    tool_calls[tool_id] = {
                        'name': tool_name,
                        'id': tool_id,
                        'input': ''
                    }
                
                # Accumulate input
                if input_chunk:
                    tool_calls[tool_id]['input'] += input_chunk
        
        elif event_type == 'meteringEvent':
            # Usage metrics
            if isinstance(payload, dict):
                messages.append({
                    'type': 'metering',
                    'usage': payload.get('usage', 0),
                    'unit': payload.get('unit', 'credit')
                })
        
        elif event_type == 'contextUsageEvent':
            # Context usage
            if isinstance(payload, dict):
                messages.append({
                    'type': 'context_usage',
                    'percentage': payload.get('contextUsagePercentage', 0)
                })
    
    # Add accumulated text as first message
    if text_chunks:
        messages.insert(0, {
            'type': 'text',
            'content': ''.join(text_chunks)
        })
    
    # Add tool calls
    for tool_call in tool_calls.values():
        messages.insert(1 if text_chunks else 0, {
            'type': 'tool_use',
            'name': tool_call['name'],
            'id': tool_call['id'],
            'input': tool_call['input']
        })
    
    return messages

def main():
    """Process all decoded JSON files"""
    # Get paths relative to script location
    script_dir = Path(__file__).parent.parent  # Go up to _kiropipe
    responses_dir = script_dir / 'debug_logs' / 'interactions' / 'responses'
    json_files = sorted(responses_dir.glob('response_binary_*.json'))
    
    if not json_files:
        print("No decoded JSON files found.")
        print("Run decode_event_stream.py first.")
        return
    
    print("\n" + "="*60)
    print("Reconstructed AI Messages")
    print("="*60 + "\n")
    
    for jf in json_files:
        with open(jf, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        message, metadata = reconstruct_message(events)
        
        print(f"\n{'='*60}")
        print(f"File: {jf.name}")
        print(f"{'='*60}")
        print(f"\nFull Message ({len(message)} chars):")
        print("-" * 60)
        print(message)
        print("-" * 60)
        
        if metadata['metering']:
            print(f"\nUsage: {metadata['metering']['usage']:.4f} {metadata['metering']['unitPlural']}")
        
        if metadata['context_usage']:
            print(f"Context: {metadata['context_usage']['contextUsagePercentage']:.2f}%")
        
        print()

if __name__ == '__main__':
    main()
