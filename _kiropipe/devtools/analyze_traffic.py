#!/usr/bin/env python3
"""
Traffic Analysis Tool
Consolidated tool for analyzing captured AWS Q traffic

Combines functionality from:
- analyze_interaction_pattern.py
- analyze_request_response_pairs.py
- analyze_responses.py
- inspect_request_structure.py
- unpack_request.py
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.decode_event_stream import decode_event_stream


def analyze_request(request_file: Path):
    """Analyze a single request file"""
    print(f"\n{'='*60}")
    print(f"Request: {request_file.name}")
    print(f"{'='*60}")
    
    with open(request_file, 'r') as f:
        data = json.load(f)
    
    body = json.loads(data['body']) if isinstance(data['body'], str) else data['body']
    
    # Extract key information
    conv_state = body.get('conversationState', {})
    conv_id = conv_state.get('conversationId', 'N/A')
    
    current_msg = conv_state.get('currentMessage', {})
    user_input = current_msg.get('userInputMessage', {})
    content = user_input.get('content', '')
    
    history = conv_state.get('history', [])
    
    # Check for tools
    context = user_input.get('userInputMessageContext', {})
    tools = context.get('tools', [])
    tool_results = context.get('toolResults', [])
    
    print(f"\nConversation ID: {conv_id}")
    print(f"User message: {content[:100]}...")
    print(f"History items: {len(history)}")
    print(f"Tools available: {len(tools)}")
    print(f"Tool results: {len(tool_results)}")
    
    if tools:
        print(f"\nTools:")
        for tool in tools[:3]:
            tool_spec = tool.get('toolSpecification', tool)
            print(f"  - {tool_spec.get('name')}: {tool_spec.get('description', '')[:50]}")
    
    if tool_results:
        print(f"\nTool Results:")
        for result in tool_results:
            print(f"  - {result.get('toolUseId')}: {result.get('status')}")


def analyze_response(response_file: Path):
    """Analyze a single response file"""
    print(f"\n{'='*60}")
    print(f"Response: {response_file.name}")
    print(f"{'='*60}")
    
    # Read binary response
    with open(response_file, 'rb') as f:
        binary_data = f.read()
    
    print(f"Size: {len(binary_data)} bytes")
    
    # Decode event stream
    try:
        events = decode_event_stream(binary_data)
        print(f"Events: {len(events)}")
        
        # Extract text and tool calls
        text_parts = []
        tool_calls = []
        
        for event in events:
            event_type = event['headers'].get(':event-type')
            payload = event['payload']
            
            if event_type == 'assistantResponseEvent':
                if 'content' in payload:
                    text_parts.append(payload['content'])
            
            elif event_type == 'toolUseEvent':
                tool_calls.append({
                    'name': payload.get('name'),
                    'id': payload.get('toolUseId'),
                    'input': payload.get('input', '')[:100]
                })
        
        if text_parts:
            full_text = ''.join(text_parts)
            print(f"\nText response ({len(full_text)} chars):")
            print(f"  {full_text[:200]}...")
        
        if tool_calls:
            print(f"\nTool calls:")
            for tc in tool_calls:
                print(f"  - {tc['name']} ({tc['id']})")
                print(f"    Input: {tc['input']}...")
    
    except Exception as e:
        print(f"Error decoding: {e}")


def analyze_pair(request_file: Path, response_file: Path):
    """Analyze request-response pair"""
    analyze_request(request_file)
    analyze_response(response_file)


def analyze_all(interactions_dir: Path):
    """Analyze all interactions in directory"""
    posted_dir = interactions_dir / 'posted'
    responses_dir = interactions_dir / 'responses'
    
    if not posted_dir.exists() or not responses_dir.exists():
        print(f"Error: Directories not found")
        print(f"  Posted: {posted_dir}")
        print(f"  Responses: {responses_dir}")
        return
    
    # Get all request files
    request_files = sorted(posted_dir.glob('request_*.json'))
    
    print(f"\nFound {len(request_files)} interactions")
    
    for req_file in request_files:
        # Find corresponding response
        num = req_file.stem.split('_')[1]
        resp_file = responses_dir / f'response_{num}.bin'
        
        if resp_file.exists():
            analyze_pair(req_file, resp_file)
        else:
            print(f"\nWarning: No response for {req_file.name}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python analyze_traffic.py <interactions_dir>  # Analyze all")
        print("  python analyze_traffic.py <request.json>      # Analyze request")
        print("  python analyze_traffic.py <response.bin>      # Analyze response")
        return
    
    path = Path(sys.argv[1])
    
    if path.is_dir():
        analyze_all(path)
    elif path.suffix == '.json':
        analyze_request(path)
    elif path.suffix == '.bin':
        analyze_response(path)
    else:
        print(f"Unknown file type: {path}")


if __name__ == '__main__':
    main()
