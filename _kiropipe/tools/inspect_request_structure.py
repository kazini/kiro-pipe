#!/usr/bin/env python3
"""
Inspect Request Structure
Deep dive into what's actually in AWS Q requests
"""

import json
import sys
from pathlib import Path


def inspect_request(request_num):
    """Inspect a specific request in detail"""
    script_dir = Path(__file__).parent.parent
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    
    request_file = posted_dir / f'request_{request_num}.json'
    if not request_file.exists():
        print(f"Request {request_num} not found")
        return
    
    with open(request_file, 'r') as f:
        request_data = json.load(f)
    
    # Parse request body
    body = json.loads(request_data['body'])
    
    print(f"\n{'='*80}")
    print(f"REQUEST #{request_num} - FULL STRUCTURE")
    print(f"{'='*80}\n")
    
    # Show size
    body_str = json.dumps(body, indent=2)
    print(f"Total Size: {len(request_data['body'])} bytes")
    print(f"Formatted Size: {len(body_str)} bytes\n")
    
    # Top level keys
    print("Top Level Keys:")
    for key in body.keys():
        print(f"  - {key}")
    
    # Conversation state
    conv_state = body.get('conversationState', {})
    print(f"\nConversation State Keys:")
    for key in conv_state.keys():
        print(f"  - {key}")
    
    # Current message
    current_msg = conv_state.get('currentMessage', {})
    print(f"\nCurrent Message Keys:")
    for key in current_msg.keys():
        print(f"  - {key}")
    
    # User input message
    user_input = current_msg.get('userInputMessage', {})
    print(f"\nUser Input Message Keys:")
    for key in user_input.keys():
        print(f"  - {key}")
    
    content = user_input.get('content', '')
    print(f"\nContent: {len(content)} chars")
    if content:
        print(f"  {content[:200]}...")
    
    # Context
    context = user_input.get('userInputMessageContext', {})
    print(f"\nUser Input Message Context Keys:")
    for key in context.keys():
        value = context[key]
        if isinstance(value, list):
            print(f"  - {key}: {len(value)} items")
        elif isinstance(value, dict):
            print(f"  - {key}: {len(value)} keys")
        else:
            print(f"  - {key}: {type(value).__name__}")
    
    # Tool results
    tool_results = context.get('toolResults', [])
    if tool_results:
        print(f"\nTool Results: {len(tool_results)}")
        for i, result in enumerate(tool_results[:3], 1):
            tool_id = result.get('toolUseId', '')
            status = result.get('status', '')
            content_items = result.get('content', [])
            
            total_text = 0
            for item in content_items:
                if isinstance(item, dict) and 'text' in item:
                    total_text += len(item['text'])
            
            print(f"  {i}. {tool_id[:40]}...")
            print(f"     Status: {status}")
            print(f"     Content: {total_text} chars")
    
    # Tools
    tools = context.get('tools', [])
    if tools:
        print(f"\nTools: {len(tools)}")
        
        total_tool_size = 0
        for tool in tools:
            tool_str = json.dumps(tool)
            total_tool_size += len(tool_str)
        
        print(f"  Total size: {total_tool_size} bytes")
        print(f"  Average per tool: {total_tool_size // len(tools)} bytes")
        
        # Show first few tools
        for i, tool in enumerate(tools[:5], 1):
            tool_spec = tool.get('toolSpecification', tool)
            name = tool_spec.get('name', 'unknown')
            desc = tool_spec.get('description', '')
            print(f"\n  {i}. {name}")
            print(f"     Description: {len(desc)} chars")
            if desc:
                print(f"     {desc[:100]}...")
    
    # Check for other context items
    for key, value in context.items():
        if key not in ['tools', 'toolResults']:
            print(f"\n{key}:")
            if isinstance(value, str):
                print(f"  {len(value)} chars")
                print(f"  {value[:200]}...")
            elif isinstance(value, list):
                print(f"  {len(value)} items")
                if value and isinstance(value[0], dict):
                    print(f"  First item keys: {list(value[0].keys())}")
            elif isinstance(value, dict):
                print(f"  Keys: {list(value.keys())}")
    
    # Check for history or previous messages
    print(f"\n{'='*80}")
    print("LOOKING FOR CONVERSATION HISTORY...")
    print(f"{'='*80}\n")
    
    # Check all keys recursively
    def find_history(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                if 'history' in key.lower() or 'previous' in key.lower() or 'messages' in key.lower():
                    print(f"Found: {new_path}")
                    if isinstance(value, list):
                        print(f"  Type: list with {len(value)} items")
                    elif isinstance(value, str):
                        print(f"  Type: string with {len(value)} chars")
                    else:
                        print(f"  Type: {type(value).__name__}")
                find_history(value, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                find_history(item, f"{path}[{i}]")
    
    find_history(body)
    
    # Show full JSON structure (truncated)
    print(f"\n{'='*80}")
    print("FULL JSON STRUCTURE (truncated)")
    print(f"{'='*80}\n")
    
    # Truncate large fields
    def truncate_large_fields(obj, max_len=200):
        if isinstance(obj, dict):
            return {k: truncate_large_fields(v, max_len) for k, v in obj.items()}
        elif isinstance(obj, list):
            if len(obj) > 3:
                return [truncate_large_fields(obj[0], max_len), "...", f"({len(obj)} items total)"]
            return [truncate_large_fields(item, max_len) for item in obj]
        elif isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + f"... ({len(obj)} chars total)"
        return obj
    
    truncated = truncate_large_fields(body)
    print(json.dumps(truncated, indent=2))


def main():
    """Inspect recent requests"""
    script_dir = Path(__file__).parent.parent
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    
    if not posted_dir.exists():
        print("No captured requests found.")
        return
    
    requests = sorted(posted_dir.glob('request_*.json'))
    
    if not requests:
        print("No requests found.")
        return
    
    print("\n" + "="*80)
    print("AVAILABLE REQUESTS")
    print("="*80 + "\n")
    
    for req_file in requests[-10:]:
        req_num = req_file.stem.split('_')[1]
        size = req_file.stat().st_size
        print(f"  Request #{req_num}: {size:,} bytes")
    
    print("\nInspecting largest request...\n")
    
    # Find largest
    largest = max(requests, key=lambda f: f.stat().st_size)
    req_num = largest.stem.split('_')[1]
    
    inspect_request(req_num)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Inspect specific request
        inspect_request(sys.argv[1])
    else:
        # Inspect largest
        main()
