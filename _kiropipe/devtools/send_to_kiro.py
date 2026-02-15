#!/usr/bin/env python3
"""
Send to Kiro - Inject a message directly into Kiro
This simulates sending a message through the bridge to Kiro
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


def get_kiropipe_url():
    """Get the kiropipe proxy URL"""
    # kiropipe.py runs mitmproxy on a specific port
    # Default is 29974 as defined in kiropipe.py
    return 'http://localhost:29974'


def send_to_kiro(message: str, conversation_id: str = None):
    """
    Send a message to Kiro through kiropipe
    
    Args:
        message: The message to send
        conversation_id: Optional conversation ID (generates new if None)
    """
    import uuid
    
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())
    
    print(f"\n{'='*60}")
    print("Send to Kiro")
    print(f"{'='*60}")
    print(f"Message: {message}")
    print(f"Conversation ID: {conversation_id}")
    print(f"{'='*60}\n")
    
    # Build AWS Q format request (what Kiro sends)
    request_data = {
        'conversationState': {
            'conversationId': conversation_id,
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
    
    # Send to AWS Q endpoint (which kiropipe intercepts)
    aws_url = 'https://q.us-east-1.amazonaws.com/generateAssistantResponse'
    
    print("Sending request to AWS Q endpoint...")
    print("(kiropipe.py should intercept this)\n")
    
    try:
        # This goes through kiropipe proxy if it's running
        response = httpx.post(
            aws_url,
            json=request_data,
            timeout=30.0,
            # Use system proxy settings (kiropipe sets these)
            follow_redirects=True
        )
        
        if response.status_code == 200:
            print(f"✓ Received response: {len(response.content)} bytes")
            print(f"✓ Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            # Check if it's binary (AWS Event Stream)
            if 'eventstream' in response.headers.get('content-type', ''):
                print("✓ Response is AWS Event Stream format")
                
                # Decode and display
                from engine.decode_event_stream import decode_event_stream
                
                events = decode_event_stream(response.content)
                print(f"✓ Decoded {len(events)} events\n")
                
                print(f"{'='*60}")
                print("Response:")
                print(f"{'='*60}\n")
                
                # Display streaming
                for event in events:
                    event_type = event['headers'].get(':event-type', '')
                    payload = event['payload']
                    
                    if event_type == 'assistantResponseEvent':
                        if isinstance(payload, dict) and 'content' in payload:
                            print(payload['content'], end='', flush=True)
                    
                    elif event_type == 'toolUseEvent':
                        if isinstance(payload, dict):
                            tool_name = payload.get('name', '')
                            tool_id = payload.get('toolUseId', '')
                            print(f"\n\n[Tool Call: {tool_name}]")
                            print(f"ID: {tool_id}")
                    
                    elif event_type == 'meteringEvent':
                        if isinstance(payload, dict):
                            usage = payload.get('usage', 0)
                            print(f"\n\n[Usage: {usage} credits]")
                    
                    elif event_type == 'contextUsageEvent':
                        if isinstance(payload, dict):
                            pct = payload.get('contextUsagePercentage', 0)
                            print(f"[Context: {pct:.1f}%]")
                
                print(f"\n\n{'='*60}")
                print("✓ Message sent successfully!")
                print(f"{'='*60}\n")
                
                return True
            else:
                print("✗ Response is not AWS Event Stream format")
                print(f"Response: {response.text[:200]}")
                return False
        else:
            print(f"✗ Error: HTTP {response.status_code}")
            print(response.text)
            return False
    
    except httpx.ConnectError as e:
        print(f"✗ Connection Error: {e}")
        print("\nMake sure kiropipe.py is running:")
        print("  python kiropipe.py")
        print("\nAnd ENABLE_BRIDGE is set to True in kiropipe.py")
        return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("\nUsage: python send_to_kiro.py \"Your message here\" [conversation_id]")
        print("\nExamples:")
        print("  python _kiropipe/tools/send_to_kiro.py \"Hello, how are you?\"")
        print("  python _kiropipe/tools/send_to_kiro.py \"Continue\" abc-123-def")
        print("\nPrerequisites:")
        print("  1. Start injection server:")
        print("     python _kiropipe/tools/inject_response.py")
        print("\n  2. Configure kiropipe.py:")
        print("     ENABLE_BRIDGE = True")
        print("     BRIDGE_URL = 'http://localhost:8132'  # or whatever port")
        print("\n  3. Launch Kiro:")
        print("     python kiropipe.py")
        print("\n  4. Send message:")
        print("     python _kiropipe/tools/send_to_kiro.py \"Hello!\"")
        print()
        return 1
    
    message = sys.argv[1]
    conversation_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = send_to_kiro(message, conversation_id)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
