#!/usr/bin/env python3
"""
Kiro API Bridge Server
FastAPI server that translates between AWS Q and standard LLM APIs
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.request_translator import translate_to_anthropic, translate_to_openai
from engine.response_translator import translate_anthropic_stream, translate_openai_stream

# ============================================================
# CONFIGURATION
# ============================================================
BRIDGE_CONFIG = {
    'backend': 'litellm',  # 'anthropic', 'openai', or 'litellm'
    'model': 'ollama/llama3.2',
    'api_key': None,  # Set via environment or config
    'api_base': None,  # Optional custom base URL
    'max_tokens': 4096,
    'debug': True,
}

# LiteLLM configuration (if using LiteLLM)
LITELLM_CONFIG = {
    'enabled': True,
    'model': 'ollama/llama3.2',
    'api_base': 'http://localhost:11434',
    'api_key': None,
}

# Session tracking
SESSION_STATS = {
    'total_requests': 0,
    'total_input_tokens': 0,
    'total_output_tokens': 0,
    'total_tokens': 0,
    'sessions': {}  # conversation_id -> stats
}
# ============================================================

app = FastAPI(title="Kiro API Bridge", version="1.0.0")


def call_anthropic_api(request_body: Dict[str, Any]) -> Any:
    """Call Anthropic API"""
    import anthropic
    
    api_key = BRIDGE_CONFIG.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("Anthropic API key not configured. Set 'api_key' in config or ANTHROPIC_API_KEY environment variable.")
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Make streaming request
    with client.messages.stream(
        model=request_body['model'],
        max_tokens=request_body['max_tokens'],
        messages=request_body['messages'],
        tools=request_body.get('tools'),
    ) as stream:
        for event in stream:
            # Convert to dict format expected by translator
            if hasattr(event, 'type'):
                event_dict = {'type': event.type}
                
                # Add relevant fields based on event type
                if event.type == 'message_start':
                    event_dict['message'] = {
                        'usage': {
                            'input_tokens': event.message.usage.input_tokens if hasattr(event.message, 'usage') else 0
                        }
                    }
                elif event.type == 'content_block_start':
                    if hasattr(event, 'content_block'):
                        cb = event.content_block
                        event_dict['content_block'] = {
                            'type': cb.type if hasattr(cb, 'type') else 'text'
                        }
                        if hasattr(cb, 'id'):
                            event_dict['content_block']['id'] = cb.id
                        if hasattr(cb, 'name'):
                            event_dict['content_block']['name'] = cb.name
                elif event.type == 'content_block_delta':
                    if hasattr(event, 'delta'):
                        delta = event.delta
                        event_dict['delta'] = {'type': delta.type if hasattr(delta, 'type') else 'text_delta'}
                        if hasattr(delta, 'text'):
                            event_dict['delta']['text'] = delta.text
                        if hasattr(delta, 'partial_json'):
                            event_dict['delta']['partial_json'] = delta.partial_json
                    if hasattr(event, 'index'):
                        event_dict['index'] = event.index
                elif event.type == 'message_delta':
                    if hasattr(event, 'usage'):
                        event_dict['usage'] = {
                            'output_tokens': event.usage.output_tokens if hasattr(event.usage, 'output_tokens') else 0
                        }
                
                yield event_dict


def call_openai_api(request_body: Dict[str, Any]) -> Any:
    """Call OpenAI API"""
    from openai import OpenAI
    
    api_key = BRIDGE_CONFIG.get('api_key') or os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not configured. Set 'api_key' in config or OPENAI_API_KEY environment variable.")
    
    client = OpenAI(api_key=api_key)
    
    # Make streaming request
    stream = client.chat.completions.create(
        model=request_body['model'],
        max_tokens=request_body['max_tokens'],
        messages=request_body['messages'],
        tools=request_body.get('tools'),
        stream=True
    )
    
    for chunk in stream:
        # Convert to dict
        yield json.loads(chunk.model_dump_json())


def call_litellm_api(request_body: Dict[str, Any]) -> Any:
    """Call LiteLLM (universal LLM interface)"""
    from litellm import completion
    
    # Get API key from config or environment
    api_key = LITELLM_CONFIG.get('api_key')
    if not api_key:
        # Try environment variables based on model
        model = LITELLM_CONFIG['model']
        if 'groq' in model.lower():
            api_key = os.environ.get('GROQ_API_KEY')
        elif 'openai' in model.lower():
            api_key = os.environ.get('OPENAI_API_KEY')
        elif 'anthropic' in model.lower() or 'claude' in model.lower():
            api_key = os.environ.get('ANTHROPIC_API_KEY')
        # Ollama doesn't need API key
    
    response = completion(
        model=LITELLM_CONFIG['model'],
        messages=request_body['messages'],
        tools=request_body.get('tools'),
        stream=True,
        api_base=LITELLM_CONFIG.get('api_base'),
        api_key=api_key,
        max_tokens=request_body['max_tokens']
    )
    
    for chunk in response:
        # LiteLLM returns OpenAI-compatible format
        if hasattr(chunk, 'model_dump'):
            yield chunk.model_dump()
        else:
            yield chunk


async def generate_aws_stream(aws_request: Dict[str, Any], conversation_id: str = None) -> bytes:
    """Generate AWS Event Stream response from AWS Q request"""
    backend = BRIDGE_CONFIG['backend']
    
    # Track session
    if conversation_id:
        if conversation_id not in SESSION_STATS['sessions']:
            SESSION_STATS['sessions'][conversation_id] = {
                'requests': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0
            }
        SESSION_STATS['sessions'][conversation_id]['requests'] += 1
    
    SESSION_STATS['total_requests'] += 1
    
    if BRIDGE_CONFIG['debug']:
        print(f"\n[Bridge] Backend: {backend}")
        print(f"[Bridge] Model: {BRIDGE_CONFIG['model']}")
        if conversation_id:
            print(f"[Bridge] Conversation ID: {conversation_id}")
            print(f"[Bridge] Session requests: {SESSION_STATS['sessions'][conversation_id]['requests']}")
    
    # Track usage for this request
    request_input_tokens = 0
    request_output_tokens = 0
    
    # Translate request based on backend
    if backend == 'anthropic' or (backend == 'litellm' and 'claude' in LITELLM_CONFIG['model']):
        translated_request = translate_to_anthropic(
            aws_request,
            model=BRIDGE_CONFIG['model'],
            max_tokens=BRIDGE_CONFIG['max_tokens']
        )
        
        if BRIDGE_CONFIG['debug']:
            print(f"[Bridge] Translated to Anthropic format")
            print(f"[Bridge] Messages: {len(translated_request['messages'])}")
            if translated_request.get('tools'):
                print(f"[Bridge] Tools: {len(translated_request['tools'])}")
        
        # Call API
        if backend == 'anthropic':
            response_stream = call_anthropic_api(translated_request)
        else:
            response_stream = call_litellm_api(translated_request)
        
        # Translate response to AWS Event Stream and track usage
        for chunk in translate_anthropic_stream(response_stream):
            yield chunk
    
    elif backend == 'openai' or backend == 'litellm':
        translated_request = translate_to_openai(
            aws_request,
            model=BRIDGE_CONFIG['model'] if backend == 'openai' else LITELLM_CONFIG['model'],
            max_tokens=BRIDGE_CONFIG['max_tokens']
        )
        
        if BRIDGE_CONFIG['debug']:
            print(f"[Bridge] Translated to OpenAI format")
            print(f"[Bridge] Messages: {len(translated_request['messages'])}")
            if translated_request.get('tools'):
                print(f"[Bridge] Tools: {len(translated_request['tools'])}")
        
        # Call API
        if backend == 'openai':
            response_stream = call_openai_api(translated_request)
        else:
            response_stream = call_litellm_api(translated_request)
        
        # Translate response to AWS Event Stream
        for chunk in translate_openai_stream(response_stream):
            yield chunk
    
    else:
        raise ValueError(f"Unknown backend: {backend}")


@app.post("/generateAssistantResponse")
async def generate_assistant_response(request: Request):
    """
    Main endpoint that mimics AWS Q API
    Receives AWS Q format, returns AWS Event Stream
    """
    try:
        # Parse AWS Q request
        aws_request = await request.json()
        
        # Extract conversation ID for session tracking
        conversation_id = None
        try:
            conversation_id = aws_request.get('conversationState', {}).get('conversationId')
        except:
            pass
        
        if BRIDGE_CONFIG['debug']:
            print(f"\n{'='*60}")
            print("[Bridge] Received AWS Q request")
            print(f"{'='*60}")
            
            # Extract user message for logging
            try:
                conv_state = aws_request.get('conversationState', {})
                current_msg = conv_state.get('currentMessage', {})
                user_input = current_msg.get('userInputMessage', {})
                content = user_input.get('content', '')
                print(f"[Bridge] User message: {content[:100]}...")
            except:
                pass
        
        # Generate AWS Event Stream response
        return StreamingResponse(
            generate_aws_stream(aws_request, conversation_id),
            media_type='application/vnd.amazon.eventstream',
            headers={
                'Content-Type': 'application/vnd.amazon.eventstream',
                'x-amzn-requestid': 'bridge-' + str(hash(str(aws_request)))[:16],
            }
        )
    
    except Exception as e:
        if BRIDGE_CONFIG['debug']:
            print(f"[Bridge] Error: {e}")
            import traceback
            traceback.print_exc()
        
        return Response(
            content=json.dumps({'error': str(e)}),
            status_code=500,
            media_type='application/json'
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'ok',
        'backend': BRIDGE_CONFIG['backend'],
        'model': BRIDGE_CONFIG['model'],
        'litellm_enabled': LITELLM_CONFIG['enabled'],
        'stats': {
            'total_requests': SESSION_STATS['total_requests'],
            'total_tokens': SESSION_STATS['total_tokens'],
            'active_sessions': len(SESSION_STATS['sessions'])
        }
    }


@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    return {
        'backend': BRIDGE_CONFIG['backend'],
        'model': BRIDGE_CONFIG['model'],
        'max_tokens': BRIDGE_CONFIG['max_tokens'],
        'api_key_configured': bool(BRIDGE_CONFIG.get('api_key')),
        'litellm': {
            'enabled': LITELLM_CONFIG['enabled'],
            'model': LITELLM_CONFIG['model'],
            'api_base': LITELLM_CONFIG['api_base'],
            'api_key_configured': bool(LITELLM_CONFIG.get('api_key'))
        }
    }


@app.get("/stats")
async def get_stats():
    """Get detailed usage statistics"""
    return {
        'total_requests': SESSION_STATS['total_requests'],
        'total_input_tokens': SESSION_STATS['total_input_tokens'],
        'total_output_tokens': SESSION_STATS['total_output_tokens'],
        'total_tokens': SESSION_STATS['total_tokens'],
        'sessions': {
            conv_id: {
                'requests': stats['requests'],
                'input_tokens': stats['input_tokens'],
                'output_tokens': stats['output_tokens'],
                'total_tokens': stats['total_tokens']
            }
            for conv_id, stats in SESSION_STATS['sessions'].items()
        }
    }


def load_config_from_file(config_path: str = '_kiropipe/kiropipe_config.json'):
    """Load configuration from JSON file"""
    config_file = Path(__file__).parent.parent / 'kiropipe_config.json'
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update BRIDGE_CONFIG
            if 'bridge' in config:
                BRIDGE_CONFIG.update(config['bridge'])
            
            # Update LITELLM_CONFIG
            if 'litellm' in config:
                LITELLM_CONFIG.update(config['litellm'])
            
            print(f"[Bridge] Loaded configuration from {config_file}")
            
            # Validate configuration
            if BRIDGE_CONFIG['backend'] == 'anthropic' and not BRIDGE_CONFIG.get('api_key') and not os.environ.get('ANTHROPIC_API_KEY'):
                print(f"[Bridge] WARNING: Anthropic backend selected but no API key configured")
            elif BRIDGE_CONFIG['backend'] == 'openai' and not BRIDGE_CONFIG.get('api_key') and not os.environ.get('OPENAI_API_KEY'):
                print(f"[Bridge] WARNING: OpenAI backend selected but no API key configured")
            elif BRIDGE_CONFIG['backend'] == 'litellm':
                model = LITELLM_CONFIG['model']
                if 'groq' in model.lower() and not LITELLM_CONFIG.get('api_key') and not os.environ.get('GROQ_API_KEY'):
                    print(f"[Bridge] WARNING: Groq model selected but no API key configured")
                elif 'ollama' in model.lower():
                    print(f"[Bridge] Using Ollama (no API key needed)")
            
            return True
        except Exception as e:
            print(f"[Bridge] Warning: Failed to load config: {e}")
    else:
        print(f"[Bridge] No config file found at {config_file}")
        print(f"[Bridge] Using default configuration (Ollama)")
        print(f"[Bridge] To customize, copy kiropipe_config.json.example to kiropipe_config.json")
    
    return False


if __name__ == '__main__':
    import os
    from pathlib import Path
    
    # Load config from file if exists
    load_config_from_file()
    
    # Get port from environment or find a free one
    port = int(os.environ.get('BRIDGE_PORT', 0))
    if port == 0:
        # Find a free port
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
    
    # Write port to file for auto-detection
    port_file = Path(__file__).parent.parent / 'debug_logs' / '.server_port'
    port_file.parent.mkdir(parents=True, exist_ok=True)
    port_file.write_text(str(port))
    
    print("\n" + "="*60)
    print("Kiro API Bridge Server")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  - Backend: {BRIDGE_CONFIG['backend']}")
    print(f"  - Model: {BRIDGE_CONFIG['model']}")
    print(f"  - Max tokens: {BRIDGE_CONFIG['max_tokens']}")
    print(f"  - Debug mode: {BRIDGE_CONFIG['debug']}")
    
    # Show API key status
    if BRIDGE_CONFIG['backend'] == 'anthropic':
        api_key = BRIDGE_CONFIG.get('api_key') or os.environ.get('ANTHROPIC_API_KEY')
        print(f"  - API key: {'✓ Configured' if api_key else '✗ Not configured'}")
    elif BRIDGE_CONFIG['backend'] == 'openai':
        api_key = BRIDGE_CONFIG.get('api_key') or os.environ.get('OPENAI_API_KEY')
        print(f"  - API key: {'✓ Configured' if api_key else '✗ Not configured'}")
    
    if LITELLM_CONFIG['enabled']:
        print(f"\nLiteLLM:")
        print(f"  - Model: {LITELLM_CONFIG['model']}")
        print(f"  - API base: {LITELLM_CONFIG['api_base']}")
        
        # Check API key for cloud providers
        model = LITELLM_CONFIG['model']
        if 'groq' in model.lower():
            api_key = LITELLM_CONFIG.get('api_key') or os.environ.get('GROQ_API_KEY')
            print(f"  - API key: {'✓ Configured' if api_key else '✗ Not configured (required for Groq)'}")
        elif 'ollama' in model.lower():
            print(f"  - API key: Not required (local Ollama)")
    
    print(f"\nEndpoints:")
    print(f"  - POST http://localhost:{port}/generateAssistantResponse")
    print(f"  - GET  http://localhost:{port}/health")
    print(f"  - GET  http://localhost:{port}/config")
    print(f"  - GET  http://localhost:{port}/stats")
    
    print(f"\nUsage:")
    print(f"  1. Update kiropipe.py:")
    print(f"     ENABLE_BRIDGE = True")
    print(f"     BRIDGE_URL = 'http://localhost:{port}'")
    print(f"  2. Run: python kiropipe.py")
    
    print(f"\nPort file: {port_file}")
    print(f"  (Auto-detected by test tools)")
    print("\n" + "="*60 + "\n")
    
    try:
        # Run server
        uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')
    finally:
        # Clean up port file
        if port_file.exists():
            port_file.unlink()
