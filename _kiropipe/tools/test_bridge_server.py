#!/usr/bin/env python3
"""
Test Bridge Server
Simple test to verify the bridge server is working
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_request_translation():
    """Test that request translation works"""
    from engine.request_translator import translate_to_anthropic
    
    print("\n" + "="*60)
    print("Test 1: Request Translation")
    print("="*60 + "\n")
    
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Hello, how are you?',
                    'userInputMessageContext': {
                        'tools': [
                            {
                                'name': 'readFile',
                                'description': 'Read a file',
                                'inputSchema': {
                                    'type': 'object',
                                    'properties': {
                                        'path': {'type': 'string'}
                                    },
                                    'required': ['path']
                                }
                            }
                        ]
                    }
                }
            }
        }
    }
    
    anthropic_req = translate_to_anthropic(aws_request)
    
    print("✓ Request translated successfully")
    print(f"  Model: {anthropic_req['model']}")
    print(f"  Messages: {len(anthropic_req['messages'])}")
    print(f"  Tools: {len(anthropic_req.get('tools', []))}")
    print(f"  Stream: {anthropic_req['stream']}")
    
    return True


def test_response_translation():
    """Test that response translation works"""
    from engine.response_translator import translate_anthropic_stream
    from engine.decode_event_stream import decode_event_stream
    
    print("\n" + "="*60)
    print("Test 2: Response Translation")
    print("="*60 + "\n")
    
    # Simulate Anthropic response
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 100}}},
        {'type': 'content_block_start', 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Hello'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': ' world'}},
        {'type': 'content_block_stop'},
        {'type': 'message_delta', 'usage': {'output_tokens': 50}},
        {'type': 'message_stop'}
    ]
    
    # Translate to AWS Event Stream
    aws_stream = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    
    # Decode to verify
    events = decode_event_stream(aws_stream)
    
    print(f"✓ Response translated successfully")
    print(f"  Generated: {len(aws_stream)} bytes")
    print(f"  Events: {len(events)}")
    
    for i, event in enumerate(events, 1):
        event_type = event['headers'].get(':event-type')
        print(f"    {i}. {event_type}")
    
    return True


def test_config_loading():
    """Test configuration loading"""
    print("\n" + "="*60)
    print("Test 3: Configuration")
    print("="*60 + "\n")
    
    config_file = Path(__file__).parent.parent / 'kiropipe_config.json'
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print("✓ Configuration file found")
        print(f"  Backend: {config.get('bridge', {}).get('backend')}")
        print(f"  Model: {config.get('bridge', {}).get('model')}")
        print(f"  LiteLLM enabled: {config.get('litellm', {}).get('enabled')}")
    else:
        print("⚠ No configuration file found")
        print(f"  Expected: {config_file}")
        print(f"  Copy kiropipe_config.json.example to kiropipe_config.json")
    
    return True


def test_dependencies():
    """Test that required dependencies are installed"""
    print("\n" + "="*60)
    print("Test 4: Dependencies")
    print("="*60 + "\n")
    
    deps = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'anthropic': 'Anthropic (optional)',
        'openai': 'OpenAI (optional)',
        'litellm': 'LiteLLM (optional)'
    }
    
    for module, name in deps.items():
        try:
            __import__(module)
            print(f"✓ {name}")
        except ImportError:
            if 'optional' in name:
                print(f"⚠ {name} - not installed")
            else:
                print(f"✗ {name} - REQUIRED")
    
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Kiro API Bridge - Test Suite")
    print("="*60)
    
    tests = [
        ("Request Translation", test_request_translation),
        ("Response Translation", test_response_translation),
        ("Configuration", test_config_loading),
        ("Dependencies", test_dependencies),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60 + "\n")
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r _kiropipe/bridge_requirements.txt")
        print("2. Configure bridge: cp _kiropipe/kiropipe_config.json.example _kiropipe/kiropipe_config.json")
        print("3. Edit kiropipe_config.json with your API keys")
        print("4. Start bridge server: python _kiropipe/engine/bridge_server.py")
    else:
        print("\n✗ Some tests failed. Review output above.")
    
    print()
