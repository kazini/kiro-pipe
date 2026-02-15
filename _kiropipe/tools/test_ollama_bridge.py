#!/usr/bin/env python3
"""
Test Ollama Bridge Integration
Quick test to verify bridge server works with Ollama
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_ollama_connection():
    """Test if Ollama is running and accessible"""
    try:
        import httpx
        
        print("Testing Ollama connection...")
        response = httpx.get('http://localhost:11434/api/tags', timeout=5.0)
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama is running")
            print(f"  Available models: {len(models)}")
            for model in models:
                print(f"    - {model['name']}")
            return True
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to Ollama: {e}")
        print(f"\nTo fix:")
        print(f"  1. Install Ollama: https://ollama.ai/download")
        print(f"  2. Pull a model: ollama pull llama3.2")
        print(f"  3. Verify: ollama list")
        return False


def test_bridge_server():
    """Test if bridge server is running"""
    try:
        import httpx
        
        # Try to read port from file
        port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
        if port_file.exists():
            port = int(port_file.read_text().strip())
        else:
            print("✗ Bridge server port file not found")
            print(f"  Start bridge server: python _kiropipe/engine/bridge_server.py")
            return False, None
        
        print(f"\nTesting bridge server on port {port}...")
        response = httpx.get(f'http://localhost:{port}/health', timeout=5.0)
        
        if response.status_code == 200:
            health = response.json()
            print(f"✓ Bridge server is running")
            print(f"  Backend: {health['backend']}")
            print(f"  Model: {health['model']}")
            print(f"  Total requests: {health['stats']['total_requests']}")
            return True, port
        else:
            print(f"✗ Bridge server returned status {response.status_code}")
            return False, None
    except Exception as e:
        print(f"✗ Cannot connect to bridge server: {e}")
        print(f"\nTo fix:")
        print(f"  Start bridge server: python _kiropipe/engine/bridge_server.py")
        return False, None


def test_simple_request(port):
    """Send a simple test request to bridge"""
    try:
        import httpx
        
        print(f"\nSending test request...")
        
        # Create a simple AWS Q format request
        aws_request = {
            'conversationState': {
                'conversationId': 'test-123',
                'currentMessage': {
                    'userInputMessage': {
                        'content': 'Say hello in one sentence.',
                        'userInputMessageContext': {}
                    }
                },
                'history': []
            }
        }
        
        # Send request
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f'http://localhost:{port}/generateAssistantResponse',
                json=aws_request,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                print(f"✓ Request successful")
                print(f"  Response size: {len(response.content)} bytes")
                print(f"  Content-Type: {response.headers.get('content-type')}")
                
                # Try to decode the response
                from engine.decode_event_stream import decode_event_stream
                events = decode_event_stream(response.content)
                
                print(f"  Events received: {len(events)}")
                
                # Extract text
                text_parts = []
                for event in events:
                    event_type = event['headers'].get(':event-type')
                    if event_type == 'assistantResponseEvent':
                        payload = event['payload']
                        if 'content' in payload:
                            text_parts.append(payload['content'])
                
                if text_parts:
                    full_text = ''.join(text_parts)
                    print(f"\n  Response text:")
                    print(f"  {full_text}")
                    return True
                else:
                    print(f"  No text content found in response")
                    return False
            else:
                print(f"✗ Request failed with status {response.status_code}")
                print(f"  Response: {response.text}")
                return False
    except Exception as e:
        print(f"✗ Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("Ollama Bridge Integration Test")
    print("="*60)
    
    # Test 1: Ollama connection
    if not test_ollama_connection():
        print("\n✗ Ollama test failed")
        return False
    
    # Test 2: Bridge server
    bridge_ok, port = test_bridge_server()
    if not bridge_ok:
        print("\n✗ Bridge server test failed")
        return False
    
    # Test 3: Simple request
    if not test_simple_request(port):
        print("\n✗ Request test failed")
        return False
    
    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Edit kiropipe.py:")
    print("     ENABLE_BRIDGE = True")
    print(f"     BRIDGE_URL = 'http://localhost:{port}'")
    print("  2. Run: python kiropipe.py")
    print("  3. Open Kiro and chat!")
    print("="*60)
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
