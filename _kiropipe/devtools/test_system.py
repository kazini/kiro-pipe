#!/usr/bin/env python3
"""
System Testing Tool
Consolidated tool for testing KiroPipe components

Combines functionality from:
- test_bridge_server.py
- test_bridge_flow.py
- test_encoder.py
- test_injection.py
- test_ollama_bridge.py
- test_proxy.py
- test_real_format.py
- verify_setup.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_encoder():
    """Test event stream encoder"""
    print("\n" + "="*60)
    print("Testing Event Stream Encoder")
    print("="*60)
    
    from engine.event_stream_encoder import encode_text_chunk, encode_tool_use_chunk
    from engine.decode_event_stream import decode_event_stream
    
    # Test text encoding
    text = "Hello, world!"
    encoded = encode_text_chunk(text)
    print(f"Encoded text: {len(encoded)} bytes")
    
    # Decode and verify
    events = decode_event_stream(encoded)
    assert len(events) == 1
    assert events[0]['payload']['content'] == text
    print("[OK] Text encoding works")
    
    # Test tool use encoding
    tool_encoded = encode_tool_use_chunk("readFile", "tool_123", '{"path":"test.py"}')
    print(f"Encoded tool use: {len(tool_encoded)} bytes")
    
    tool_events = decode_event_stream(tool_encoded)
    assert len(tool_events) == 1
    print("[OK] Tool use encoding works")


def test_translators():
    """Test request/response translators"""
    print("\n" + "="*60)
    print("Testing Request/Response Translators")
    print("="*60)
    
    from engine.request_translator import translate_to_anthropic
    from engine.response_translator import translate_anthropic_stream
    
    # Test request translation
    aws_request = {
        'conversationState': {
            'conversationId': 'test-123',
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Hello',
                    'userInputMessageContext': {}
                }
            },
            'history': []
        }
    }
    
    anthropic_req = translate_to_anthropic(aws_request)
    assert 'messages' in anthropic_req
    assert len(anthropic_req['messages']) == 1
    print("[OK] Request translation works")
    
    # Test response translation
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 10}}},
        {'type': 'content_block_start', 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Hi'}},
        {'type': 'message_stop'}
    ]
    
    aws_stream = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    assert len(aws_stream) > 0
    print(f"[OK] Response translation works ({len(aws_stream)} bytes)")


def test_config():
    """Test configuration loader"""
    print("\n" + "="*60)
    print("Testing Configuration Loader")
    print("="*60)
    
    from engine.config_loader import load_config
    
    config = load_config()
    
    # Test basic access
    port = config.get('proxy.port')
    print(f"Proxy port: {port}")
    
    # Test model lookup
    model_info = config.get_model_info('kiro-default')
    assert model_info is not None
    print(f"[OK] Model lookup works")
    
    # Test providers
    providers = config.get_enabled_providers()
    print(f"Enabled providers: {', '.join(providers)}")
    print("[OK] Configuration loader works")


def test_bridge_connection():
    """Test bridge server connection"""
    print("\n" + "="*60)
    print("Testing Bridge Server Connection")
    print("="*60)
    
    try:
        import httpx
        
        # Try to read port from file
        port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
        if not port_file.exists():
            print("[SKIP] Bridge server not running (no port file)")
            return
        
        port = int(port_file.read_text().strip())
        
        # Test health endpoint
        response = httpx.get(f'http://localhost:{port}/health', timeout=5.0)
        
        if response.status_code == 200:
            health = response.json()
            print(f"[OK] Bridge server is running")
            print(f"  Backend: {health['backend']}")
            print(f"  Model: {health['model']}")
        else:
            print(f"[FAIL] Bridge server returned {response.status_code}")
    
    except Exception as e:
        print(f"[SKIP] Bridge server not accessible: {e}")


def test_ollama_connection():
    """Test Ollama connection"""
    print("\n" + "="*60)
    print("Testing Ollama Connection")
    print("="*60)
    
    try:
        import httpx
        
        response = httpx.get('http://localhost:11434/api/tags', timeout=5.0)
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"[OK] Ollama is running")
            print(f"  Models: {len(models)}")
            for model in models[:3]:
                print(f"    - {model['name']}")
        else:
            print(f"[FAIL] Ollama returned {response.status_code}")
    
    except Exception as e:
        print(f"[SKIP] Ollama not accessible: {e}")


def test_all():
    """Run all tests"""
    print("\n" + "="*60)
    print("KiroPipe System Tests")
    print("="*60)
    
    test_encoder()
    test_translators()
    test_config()
    test_bridge_connection()
    test_ollama_connection()
    
    print("\n" + "="*60)
    print("Tests Complete")
    print("="*60)


def main():
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        
        if test_name == 'encoder':
            test_encoder()
        elif test_name == 'translators':
            test_translators()
        elif test_name == 'config':
            test_config()
        elif test_name == 'bridge':
            test_bridge_connection()
        elif test_name == 'ollama':
            test_ollama_connection()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: encoder, translators, config, bridge, ollama")
    else:
        test_all()


if __name__ == '__main__':
    main()
