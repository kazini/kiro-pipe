#!/usr/bin/env python3
"""
Test Bridge Flow - Simulate the complete kiropipe.py bridge flow
This tests: Client → kiropipe (bridge) → Server → kiropipe → Client
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Install with: pip install httpx")
    sys.exit(1)

from engine.decode_event_stream import decode_event_stream


def get_server_url():
    """Get server URL from port file"""
    port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
    if port_file.exists():
        try:
            port = int(port_file.read_text().strip())
            return f'http://localhost:{port}'
        except:
            pass
    return None


def test_bridge_flow(message: str):
    """
    Test the complete bridge flow
    
    Simulates:
    1. Kiro sends AWS Q request
    2. kiropipe.py intercepts and forwards to bridge
    3. Bridge generates response
    4. kiropipe.py forwards back to Kiro
    5. Kiro displays
    
    Args:
        message: The message to send
    """
    import uuid
    
    # Get server URL
    server_url = get_server_url()
    if server_url is None:
        print("✗ No server found")
        print("\nPlease start the injection server:")
        print("  python _kiropipe/tools/inject_response.py")
        return False
    
    print(f"\n{'='*60}")
    print("Bridge Flow Test")
    print(f"{'='*60}")
    print(f"Server: {server_url}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")
    
    # Step 1: Simulate Kiro sending AWS Q request
    print("Step 1: Kiro sends request")
    print("-" * 60)
    
    request_data = {
        'conversationState': {
            'conversationId': str(uuid.uuid4()),
            'agentContinuationId': str(uuid.uuid4()),
            'agentTaskType': 'vibe',
            'chatTriggerType': 'MANUAL',
            'currentMessage': {
                'userInputMessage': {
                    'content': message,
                    'modelId': 'auto',
                    'origin': 'AI_EDITOR',
                    'userInputMessageContext': {
                        'tools': [],
                        'toolResults': []
                    }
                }
            }
        }
    }
    
    print(f"  Conversation ID: {request_data['conversationState']['conversationId']}")
    print(f"  Message: {message}")
    print()
    
    # Step 2: Simulate kiropipe.py forwarding to bridge
    print("Step 2: kiropipe.py forwards to bridge")
    print("-" * 60)
    print(f"  Bridge URL: {server_url}/generateAssistantResponse")
    print()
    
    try:
        # Step 3: Bridge processes and generates response
        print("Step 3: Bridge generates response")
        print("-" * 60)
        
        response = httpx.post(
            f'{server_url}/generateAssistantResponse',
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"✗ Error: HTTP {response.status_code}")
            print(response.text)
            return False
        
        print(f"  ✓ Response received: {len(response.content)} bytes")
        print(f"  ✓ Content-Type: {response.headers.get('content-type', 'unknown')}")
        print()
        
        # Step 4: Simulate kiropipe.py forwarding back to Kiro
        print("Step 4: kiropipe.py forwards to Kiro")
        print("-" * 60)
        print("  ✓ Binary AWS Event Stream forwarded")
        print()
        
        # Step 5: Simulate Kiro decoding and displaying
        print("Step 5: Kiro displays response")
        print("-" * 60)
        
        events = decode_event_stream(response.content)
        print(f"  ✓ Decoded {len(events)} events\n")
        
        print(f"{'='*60}")
        print("Kiro Display (simulated):")
        print(f"{'='*60}\n")
        
        # Display as Kiro would
        text_buffer = ""
        tool_calls = []
        
        for event in events:
            event_type = event['headers'].get(':event-type', '')
            payload = event['payload']
            
            if event_type == 'assistantResponseEvent':
                if isinstance(payload, dict) and 'content' in payload:
                    chunk = payload['content']
                    print(chunk, end='', flush=True)
                    text_buffer += chunk
            
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
            
            elif event_type == 'meteringEvent':
                if isinstance(payload, dict):
                    usage = payload.get('usage', 0)
                    unit = payload.get('unit', 'credit')
                    print(f"\n\n[Usage: {usage} {unit}]", flush=True)
            
            elif event_type == 'contextUsageEvent':
                if isinstance(payload, dict):
                    pct = payload.get('contextUsagePercentage', 0)
                    print(f"[Context: {pct:.1f}%]", flush=True)
        
        # Display tool calls
        if tool_calls:
            print("\n")
            for tool in tool_calls:
                print(f"\n[Tool Call: {tool['name']}]")
                print(f"ID: {tool['id']}")
                print(f"Input: {tool['input']}")
        
        print(f"\n\n{'='*60}")
        print("✓ Complete flow test successful!")
        print(f"{'='*60}")
        print("\nFlow Summary:")
        print("  1. ✓ Kiro sent request")
        print("  2. ✓ kiropipe.py forwarded to bridge")
        print("  3. ✓ Bridge generated response")
        print("  4. ✓ kiropipe.py forwarded to Kiro")
        print("  5. ✓ Kiro displayed response")
        print(f"{'='*60}\n")
        
        return True
    
    except httpx.ConnectError:
        print(f"✗ Error: Could not connect to {server_url}")
        print("\nMake sure the server is running:")
        print("  python _kiropipe/tools/inject_response.py")
        return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\nUsage: python test_bridge_flow.py \"Your message here\"")
        print("\nThis simulates the complete flow:")
        print("  Kiro → kiropipe.py → Bridge → kiropipe.py → Kiro")
        print("\nExamples:")
        print("  python _kiropipe/tools/test_bridge_flow.py \"Hello!\"")
        print("  python _kiropipe/tools/test_bridge_flow.py \"Test tool calling\"")
        print("\nPrerequisites:")
        print("  1. Start injection server:")
        print("     python _kiropipe/tools/inject_response.py")
        print("\n  2. Run this test:")
        print("     python _kiropipe/tools/test_bridge_flow.py \"Hello!\"")
        print("\nThis tests the bridge without needing to launch Kiro")
        print()
        return 1
    
    message = sys.argv[1]
    success = test_bridge_flow(message)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
