#!/usr/bin/env python3
"""
Quick Test - Send a custom message and get response
Usage: python quick_test.py "Your message here" [url]
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
    """Get the server URL from the port file"""
    port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
    
    if port_file.exists():
        try:
            port = int(port_file.read_text().strip())
            return f'http://localhost:{port}'
        except:
            pass
    
    return None


def quick_test(message: str, url: str = None):
    """
    Send a message and display the response with streaming
    
    Args:
        message: The message to send
        url: Bridge/injection server URL (reads from port file if None)
    """
    # Get server URL from port file if not specified
    if url is None:
        url = get_server_url()
        if url is None:
            print("✗ No server found")
            print("\nPlease start a server first:")
            print("  python _kiropipe/tools/inject_response.py")
            print("  or")
            print("  python _kiropipe/engine/bridge_server.py")
            print("\nOr specify URL manually:")
            print("  python _kiropipe/tools/quick_test.py \"message\" http://localhost:8000")
            return False
        print(f"Using server: {url}\n")
    
    print(f"\n{'='*60}")
    print("Quick Test")
    print(f"{'='*60}")
    print(f"Server: {url}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")
    
    # Build request
    request_data = {
        'conversationState': {
            'conversationId': 'quick-test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': message,
                    'modelId': 'auto',
                    'origin': 'AI_EDITOR'
                }
            }
        }
    }
    
    try:
        # Send request
        print("Sending request...")
        response = httpx.post(
            f'{url}/generateAssistantResponse',
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"✗ Error: HTTP {response.status_code}")
            print(response.text)
            return False
        
        print(f"✓ Received response: {len(response.content)} bytes\n")
        
        # Decode response
        events = decode_event_stream(response.content)
        print(f"✓ Decoded {len(events)} events\n")
        
        # Display response with streaming effect
        print(f"{'='*60}")
        print("Response (streaming):")
        print(f"{'='*60}\n")
        
        text_buffer = ""
        tool_calls = {}
        
        for event in events:
            event_type = event['headers'].get(':event-type', '')
            payload = event['payload']
            
            if event_type == 'assistantResponseEvent':
                # Text content - print immediately
                if isinstance(payload, dict) and 'content' in payload:
                    chunk = payload['content']
                    print(chunk, end='', flush=True)
                    text_buffer += chunk
            
            elif event_type == 'toolUseEvent':
                # Tool call - accumulate
                if isinstance(payload, dict):
                    tool_id = payload.get('toolUseId', '')
                    tool_name = payload.get('name', '')
                    input_chunk = payload.get('input', '')
                    
                    if tool_id not in tool_calls:
                        tool_calls[tool_id] = {
                            'name': tool_name,
                            'input': ''
                        }
                    
                    if input_chunk:
                        tool_calls[tool_id]['input'] += input_chunk
            
            elif event_type == 'meteringEvent':
                # Usage metrics
                if isinstance(payload, dict):
                    usage = payload.get('usage', 0)
                    unit = payload.get('unit', 'credit')
                    print(f"\n\n[Usage: {usage} {unit}]", flush=True)
            
            elif event_type == 'contextUsageEvent':
                # Context usage
                if isinstance(payload, dict):
                    percentage = payload.get('contextUsagePercentage', 0)
                    print(f"[Context: {percentage:.1f}%]", flush=True)
        
        # Display tool calls if any
        if tool_calls:
            print("\n")
            for tool_id, tool_data in tool_calls.items():
                print(f"\n[Tool Call: {tool_data['name']}]")
                print(f"ID: {tool_id}")
                print(f"Input: {tool_data['input']}")
        
        print(f"\n{'='*60}")
        print("✓ Test complete!")
        print(f"{'='*60}\n")
        
        return True
    
    except httpx.ConnectError:
        print(f"✗ Error: Could not connect to {url}")
        print("\nMake sure the server is running:")
        print("  python _kiropipe/tools/inject_response.py")
        print("  or")
        print("  python _kiropipe/engine/bridge_server.py")
        return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\nUsage: python quick_test.py \"Your message here\" [url]")
        print("\nExamples:")
        print("  python _kiropipe/tools/quick_test.py \"Hello, how are you?\"")
        print("  python _kiropipe/tools/quick_test.py \"Test tool calling\"")
        print("  python _kiropipe/tools/quick_test.py \"Hello\" http://localhost:8000")
        print("\nIf no URL is provided, will auto-detect running server")
        print("\nMake sure a server is running first:")
        print("  python _kiropipe/tools/inject_response.py")
        print("  or")
        print("  python _kiropipe/engine/bridge_server.py")
        print()
        return 1
    
    message = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = quick_test(message, url)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
