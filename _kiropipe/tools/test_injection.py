#!/usr/bin/env python3
"""
Test Response Injection
Sends a test request to the injection server to verify it works
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Install with: pip install httpx")
    sys.exit(1)

from engine.decode_event_stream import decode_event_stream
from engine.reconstruct_messages import reconstruct_messages


def get_server_url():
    """Get server URL from port file"""
    port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
    if port_file.exists():
        try:
            port = int(port_file.read_text().strip())
            return f'http://localhost:{port}'
        except:
            pass
    return 'http://localhost:8000'  # Fallback


def test_simple_response():
    """Test simple text response"""
    print("\n" + "="*60)
    print("Test 1: Simple Text Response")
    print("="*60)
    
    url = get_server_url()
    
    request_data = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Hello, how are you?',
                    'modelId': 'auto'
                }
            }
        }
    }
    
    try:
        response = httpx.post(
            f'{url}/generateAssistantResponse',
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            print(f"✓ Received response: {len(response.content)} bytes")
            
            # Decode the response
            events = decode_event_stream(response.content)
            print(f"✓ Decoded {len(events)} events")
            
            # Reconstruct message
            messages = reconstruct_messages(events)
            print(f"✓ Reconstructed {len(messages)} messages")
            
            # Display content
            for msg in messages:
                if msg['type'] == 'text':
                    print(f"\nText: {msg['content']}")
                elif msg['type'] == 'tool_use':
                    print(f"\nTool: {msg['name']}")
                    print(f"Input: {msg['input']}")
            
            print("\n✓ Test passed!")
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_call_response():
    """Test response with tool call"""
    print("\n" + "="*60)
    print("Test 2: Tool Call Response")
    print("="*60)
    
    url = get_server_url()
    
    request_data = {
        'conversationState': {
            'conversationId': 'test-456',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Please test tool calling',
                    'modelId': 'auto',
                    'userInputMessageContext': {
                        'tools': [
                            {
                                'toolSpecification': {
                                    'name': 'readFile',
                                    'description': 'Read a file',
                                    'inputSchema': {
                                        'type': 'object',
                                        'properties': {
                                            'path': {'type': 'string'}
                                        }
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
    
    try:
        response = httpx.post(
            f'{url}/generateAssistantResponse',
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            print(f"✓ Received response: {len(response.content)} bytes")
            
            # Decode the response
            events = decode_event_stream(response.content)
            print(f"✓ Decoded {len(events)} events")
            
            # Reconstruct message
            messages = reconstruct_messages(events)
            print(f"✓ Reconstructed {len(messages)} messages")
            
            # Display content
            for msg in messages:
                if msg['type'] == 'text':
                    print(f"\nText: {msg['content']}")
                elif msg['type'] == 'tool_use':
                    print(f"\nTool Call:")
                    print(f"  Name: {msg['name']}")
                    print(f"  ID: {msg['id']}")
                    print(f"  Input: {msg['input']}")
            
            print("\n✓ Test passed!")
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_result_response():
    """Test response after tool execution"""
    print("\n" + "="*60)
    print("Test 3: Tool Result Response")
    print("="*60)
    
    url = get_server_url()
    
    request_data = {
        'conversationState': {
            'conversationId': 'test-789',
            'currentMessage': {
                'userInputMessage': {
                    'content': '',
                    'modelId': 'auto',
                    'userInputMessageContext': {
                        'toolResults': [
                            {
                                'toolUseId': 'tooluse_test_12345',
                                'status': 'success',
                                'content': [
                                    {'text': 'File contents: print("Hello World")'}
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }
    
    try:
        response = httpx.post(
            f'{url}/generateAssistantResponse',
            json=request_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            print(f"✓ Received response: {len(response.content)} bytes")
            
            # Decode the response
            events = decode_event_stream(response.content)
            print(f"✓ Decoded {len(events)} events")
            
            # Reconstruct message
            messages = reconstruct_messages(events)
            print(f"✓ Reconstructed {len(messages)} messages")
            
            # Display content
            for msg in messages:
                if msg['type'] == 'text':
                    print(f"\nText: {msg['content']}")
            
            print("\n✓ Test passed!")
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)
            return False
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    import os
    
    print("\n" + "="*60)
    print("Response Injection Test Suite")
    print("="*60)
    
    # Skip prompt if running in automated mode
    if not os.environ.get('SKIP_PROMPT'):
        print("\nMake sure inject_response.py is running on port 8000")
        print("Run: python _kiropipe/tools/inject_response.py")
        print("\nPress Enter to continue...")
        input()
    else:
        print("\nRunning in automated mode...")
        print("Assuming inject_response.py is running on port 8000\n")
    
    results = []
    
    # Run tests
    results.append(("Simple Response", test_simple_response()))
    results.append(("Tool Call Response", test_tool_call_response()))
    results.append(("Tool Result Response", test_tool_result_response()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return all(p for _, p in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
