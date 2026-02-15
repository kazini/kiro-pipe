#!/usr/bin/env python3
"""
Analyze request-response patterns to detect multi-step processing
"""

import json
from pathlib import Path
from datetime import datetime

def analyze_patterns():
    """Analyze interaction patterns"""
    
    # Get paths relative to script location
    script_dir = Path(__file__).parent.parent  # Go up to _kiropipe
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    responses_dir = script_dir / 'debug_logs' / 'interactions' / 'responses'
    
    if not posted_dir.exists():
        print("No posted requests found.")
        return
    
    print("\n" + "="*80)
    print("INTERACTION PATTERN ANALYSIS")
    print("="*80 + "\n")
    
    # Get all requests
    requests = sorted(posted_dir.glob('request_*.json'))
    
    print(f"Total requests captured: {len(requests)}\n")
    
    for req_file in requests:
        req_num = req_file.stem.split('_')[1]
        
        # Read request
        with open(req_file, 'r', encoding='utf-8') as f:
            req_data = json.load(f)
        
        # Parse request body
        try:
            body = json.loads(req_data['body'])
            user_msg = body.get('conversationState', {}).get('currentMessage', {}).get('userInputMessage', {}).get('content', '')
            conv_id = body.get('conversationState', {}).get('conversationId', 'N/A')
            
            print(f"{'='*80}")
            print(f"REQUEST #{req_num}")
            print(f"{'='*80}")
            print(f"Conversation ID: {conv_id}")
            print(f"User Message: {user_msg[:200]}{'...' if len(user_msg) > 200 else ''}")
            
            # Check for tool results (indicates follow-up request)
            tool_results = body.get('conversationState', {}).get('currentMessage', {}).get('userInputMessage', {}).get('userInputMessageContext', {}).get('toolResults', [])
            if tool_results:
                print(f"\nTool Results Present: {len(tool_results)} results")
                for i, result in enumerate(tool_results[:3], 1):
                    tool_id = result.get('toolUseId', 'N/A')
                    status = result.get('status', 'N/A')
                    print(f"  {i}. Tool ID: {tool_id}, Status: {status}")
                if len(tool_results) > 3:
                    print(f"  ... and {len(tool_results) - 3} more")
            
            # Check for corresponding response
            response_files = [
                responses_dir / f'response_{req_num}.bin',
                responses_dir / f'response_{req_num}.json',
                responses_dir / f'response_binary_{req_num}.bin',
                responses_dir / f'response_binary_{req_num}.json',
            ]
            
            response_found = None
            for resp_file in response_files:
                if resp_file.exists():
                    response_found = resp_file
                    break
            
            if response_found:
                print(f"\nResponse: {response_found.name}")
                
                # If JSON, analyze content
                if response_found.suffix == '.json':
                    with open(response_found, 'r', encoding='utf-8') as f:
                        resp_data = json.load(f)
                    
                    # Count event types
                    event_types = {}
                    tool_uses = []
                    text_chunks = []
                    
                    for event in resp_data:
                        event_type = event['headers'].get(':event-type', 'unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                        
                        if event_type == 'toolUseEvent':
                            payload = event['payload']
                            tool_name = payload.get('name', 'unknown')
                            tool_id = payload.get('toolUseId', 'unknown')
                            if tool_name != 'unknown' and (tool_name, tool_id) not in [(t[0], t[1]) for t in tool_uses]:
                                tool_uses.append((tool_name, tool_id))
                        
                        elif event_type == 'assistantResponseEvent':
                            content = event['payload'].get('content', '')
                            text_chunks.append(content)
                    
                    print(f"\nEvent Types:")
                    for event_type, count in event_types.items():
                        print(f"  - {event_type}: {count}")
                    
                    if tool_uses:
                        print(f"\nTool Uses Requested:")
                        for tool_name, tool_id in tool_uses:
                            print(f"  - {tool_name} (ID: {tool_id})")
                    
                    if text_chunks:
                        full_text = ''.join(text_chunks)
                        print(f"\nResponse Text ({len(full_text)} chars):")
                        print(f"  {full_text[:300]}{'...' if len(full_text) > 300 else ''}")
                
                else:
                    print(f"  (Binary file, {response_found.stat().st_size} bytes)")
            else:
                print(f"\nResponse: NOT FOUND")
            
            print()
        
        except Exception as e:
            print(f"Error analyzing request {req_num}: {e}\n")
    
    print("="*80)
    print("\nPATTERN ANALYSIS:")
    print("-"*80)
    
    # Analyze conversation flow
    conversations = {}
    for req_file in requests:
        with open(req_file, 'r', encoding='utf-8') as f:
            req_data = json.load(f)
        
        try:
            body = json.loads(req_data['body'])
            conv_id = body.get('conversationState', {}).get('conversationId', 'unknown')
            
            if conv_id not in conversations:
                conversations[conv_id] = []
            
            conversations[conv_id].append(req_file.stem)
        except:
            pass
    
    print(f"\nConversations detected: {len(conversations)}")
    for conv_id, requests in conversations.items():
        print(f"\n  Conversation: {conv_id[:20]}...")
        print(f"  Requests: {len(requests)}")
        if len(requests) > 1:
            print(f"  Pattern: Multi-turn conversation")
            print(f"  Requests: {', '.join(requests)}")
        else:
            print(f"  Pattern: Single request")
    
    print("\n" + "="*80)
    print("\nCONCLUSION:")
    print("-"*80)
    print("""
If you see:
1. Single request → Single response: Direct LLM call, no secret sauce
2. Multiple requests with same conversation ID: Multi-turn conversation
3. Tool results in request: Follow-up after tool execution
4. Tool uses in response: LLM requesting tool execution

The pattern indicates whether AWS Q does additional processing or if it's
a straightforward LLM API call.
    """)
    print("="*80 + "\n")

if __name__ == '__main__':
    analyze_patterns()
