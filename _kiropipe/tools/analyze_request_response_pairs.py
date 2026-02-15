#!/usr/bin/env python3
"""
Analyze Request-Response Pairs
Shows the complete flow of requests and responses
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.decode_event_stream import decode_event_stream


def analyze_pair(request_num):
    """Analyze a specific request-response pair"""
    script_dir = Path(__file__).parent.parent
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    responses_dir = script_dir / 'debug_logs' / 'interactions' / 'responses'
    
    # Read request
    request_file = posted_dir / f'request_{request_num}.json'
    if not request_file.exists():
        print(f"Request {request_num} not found")
        return
    
    with open(request_file, 'r') as f:
        request_data = json.load(f)
    
    # Parse request body
    body = json.loads(request_data['body'])
    
    print(f"\n{'='*80}")
    print(f"REQUEST #{request_num}")
    print(f"{'='*80}\n")
    
    # Extract key info
    conv_state = body.get('conversationState', {})
    current_msg = conv_state.get('currentMessage', {})
    user_input = current_msg.get('userInputMessage', {})
    content = user_input.get('content', '')
    context = user_input.get('userInputMessageContext', {})
    
    print(f"User Message: {content[:200] if content else '(empty)'}")
    
    # Check for tool results
    tool_results = context.get('toolResults', [])
    if tool_results:
        print(f"\nTool Results: {len(tool_results)}")
        for i, result in enumerate(tool_results, 1):
            tool_id = result.get('toolUseId', '')
            status = result.get('status', '')
            result_content = result.get('content', [])
            
            # Extract text
            text = ''
            if isinstance(result_content, list):
                for item in result_content:
                    if isinstance(item, dict) and 'text' in item:
                        text = item['text']
                        break
            
            print(f"  {i}. {tool_id[:30]}... - {status}")
            print(f"     {text[:100]}...")
    
    # Check for tools
    tools = context.get('tools', [])
    if tools:
        print(f"\nTools Available: {len(tools)}")
        for i, tool in enumerate(tools[:3], 1):
            tool_spec = tool.get('toolSpecification', tool)
            name = tool_spec.get('name', 'unknown')
            print(f"  {i}. {name}")
        if len(tools) > 3:
            print(f"  ... and {len(tools) - 3} more")
    
    # Read response
    response_file = responses_dir / f'response_{request_num}.bin'
    if not response_file.exists():
        print(f"\nResponse: NOT FOUND")
        return
    
    with open(response_file, 'rb') as f:
        response_data = f.read()
    
    print(f"\n{'='*80}")
    print(f"RESPONSE #{request_num}")
    print(f"{'='*80}\n")
    
    print(f"Size: {len(response_data)} bytes")
    
    # Decode binary response
    try:
        events = decode_event_stream(response_data)
        print(f"Events: {len(events)}\n")
        
        # Categorize events
        text_events = []
        tool_events = []
        metering_events = []
        context_events = []
        
        for event in events:
            event_type = event['headers'].get(':event-type')
            payload = event['payload']
            
            if event_type == 'assistantResponseEvent':
                text_events.append(payload.get('content', ''))
            elif event_type == 'toolUseEvent':
                tool_events.append(payload)
            elif event_type == 'meteringEvent':
                metering_events.append(payload)
            elif event_type == 'contextUsageEvent':
                context_events.append(payload)
        
        # Show text response
        if text_events:
            full_text = ''.join(text_events)
            print(f"Text Response ({len(full_text)} chars):")
            print(f"  {full_text[:300]}...")
            if len(full_text) > 300:
                print(f"  ... (truncated)")
        
        # Show tool calls
        if tool_events:
            print(f"\nTool Calls: {len(tool_events)} events")
            
            # Group by tool ID
            tools_by_id = {}
            for event in tool_events:
                tool_id = event.get('toolUseId', '')
                if tool_id not in tools_by_id:
                    tools_by_id[tool_id] = {
                        'name': event.get('name', ''),
                        'input_chunks': []
                    }
                tools_by_id[tool_id]['input_chunks'].append(event.get('input', ''))
            
            # Show each tool
            for i, (tool_id, tool_data) in enumerate(tools_by_id.items(), 1):
                full_input = ''.join(tool_data['input_chunks'])
                print(f"\n  Tool #{i}: {tool_data['name']}")
                print(f"    ID: {tool_id}")
                print(f"    Input: {full_input[:200]}...")
        
        # Show metrics
        if metering_events:
            for event in metering_events:
                usage = event.get('usage', 0)
                unit = event.get('unit', 'credit')
                print(f"\nUsage: {usage} {unit}")
        
        if context_events:
            for event in context_events:
                pct = event.get('contextUsagePercentage', 0)
                print(f"Context: {pct:.2f}%")
        
    except Exception as e:
        print(f"Error decoding: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Analyze recent request-response pairs"""
    script_dir = Path(__file__).parent.parent
    posted_dir = script_dir / 'debug_logs' / 'interactions' / 'posted'
    
    if not posted_dir.exists():
        print("No captured requests found.")
        print("Run kiropipe.py with DEBUG_MODE=True first.")
        return
    
    # Get all requests
    requests = sorted(posted_dir.glob('request_*.json'))
    
    if not requests:
        print("No requests found.")
        return
    
    print("\n" + "="*80)
    print("REQUEST-RESPONSE PAIR ANALYSIS")
    print("="*80)
    print(f"\nTotal requests: {len(requests)}")
    
    # Analyze last 3 pairs
    print("\nAnalyzing last 3 pairs...\n")
    
    for req_file in requests[-3:]:
        req_num = req_file.stem.split('_')[1]
        analyze_pair(req_num)
    
    print("\n" + "="*80)
    print("\nKEY OBSERVATIONS:")
    print("-"*80)
    print("""
1. FIRST REQUEST: User message → LLM responds with tool calls (in binary)
2. SECOND REQUEST: Empty message + tool results → LLM responds with final answer
3. Tool calls come FROM the LLM (in response), not from Kiro
4. Kiro executes tools locally, then sends results back
5. All responses are binary AWS Event Stream format
    """)
    print("="*80 + "\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Analyze specific pair
        try:
            req_num = sys.argv[1]
            analyze_pair(req_num)
        except Exception as e:
            print(f"Error: {e}")
    else:
        # Analyze recent pairs
        main()
