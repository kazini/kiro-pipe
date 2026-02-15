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
from engine.config_loader import load_config

# ============================================================
# CONFIGURATION
# ============================================================
# Load config from YAML
CONFIG = None  # Will be loaded on startup

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


def call_anthropic_api(request_body: Dict[str, Any], api_base: Optional[str] = None, api_key: Optional[str] = None) -> Any:
    """Call Anthropic API with custom endpoint support"""
    import anthropic
    
    # Get API key
    if not api_key:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("Anthropic API key not configured. Set 'api_key' in config or ANTHROPIC_API_KEY environment variable.")
    
    # Create client with custom base URL if provided
    client_kwargs = {'api_key': api_key}
    if api_base:
        client_kwargs['base_url'] = api_base
    
    client = anthropic.Anthropic(**client_kwargs)
    
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


def call_openai_api(request_body: Dict[str, Any], api_base: Optional[str] = None, api_key: Optional[str] = None) -> Any:
    """Call OpenAI API with custom endpoint support"""
    from openai import OpenAI
    
    # Get API key
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not configured. Set 'api_key' in config or OPENAI_API_KEY environment variable.")
    
    # Create client with custom base URL if provided
    client_kwargs = {'api_key': api_key}
    if api_base:
        client_kwargs['base_url'] = api_base
    
    client = OpenAI(**client_kwargs)
    
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


def call_litellm_api(request_body: Dict[str, Any], model: str, api_base: Optional[str] = None, api_key: Optional[str] = None) -> Any:
    """Call LiteLLM (universal LLM interface) with custom endpoint support"""
    from litellm import completion
    
    # Get API key from parameter or environment
    if not api_key:
        # Try environment variables based on model
        if 'groq' in model.lower():
            api_key = os.environ.get('GROQ_API_KEY')
        elif 'openai' in model.lower():
            api_key = os.environ.get('OPENAI_API_KEY')
        elif 'anthropic' in model.lower() or 'claude' in model.lower():
            api_key = os.environ.get('ANTHROPIC_API_KEY')
        # Ollama doesn't need API key
    
    response = completion(
        model=model,
        messages=request_body['messages'],
        tools=request_body.get('tools'),
        stream=True,
        api_base=api_base,
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
    global CONFIG
    
    if not CONFIG:
        raise ValueError("Configuration not loaded")
    
    # Get model from request or use default
    requested_model = aws_request.get('model', CONFIG.get_default_model())
    
    # Look up model info
    model_info = CONFIG.get_model_info(requested_model)
    if not model_info:
        raise ValueError(f"Unknown model: {requested_model}")
    
    provider_name = model_info['provider']
    model_config = model_info['model']
    provider_config = CONFIG.get_provider_config(provider_name)
    
    if not provider_config or not provider_config.get('enabled', False):
        raise ValueError(f"Provider '{provider_name}' is not enabled")
    
    provider_type = provider_config.get('type')
    model_name = model_config.get('name')
    max_tokens = model_config.get('max_tokens', 4096)
    
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
    
    debug_mode = CONFIG.get('debug.debug_mode_enabled', False)
    
    if debug_mode:
        print(f"\n[Bridge] Provider: {provider_name} ({provider_type})")
        print(f"[Bridge] Model: {model_name}")
        if conversation_id:
            print(f"[Bridge] Conversation ID: {conversation_id}")
            print(f"[Bridge] Session requests: {SESSION_STATS['sessions'][conversation_id]['requests']}")
    
    # Handle passthrough (Kiro default models)
    if provider_type == 'passthrough':
        raise ValueError("Passthrough models should not reach the bridge server")
    
    # Translate request based on provider type
    if provider_type == 'anthropic':
        translated_request = translate_to_anthropic(
            aws_request,
            model=model_name,
            max_tokens=max_tokens
        )
        
        if debug_mode:
            print(f"[Bridge] Translated to Anthropic format")
            print(f"[Bridge] Messages: {len(translated_request['messages'])}")
            if translated_request.get('tools'):
                print(f"[Bridge] Tools: {len(translated_request['tools'])}")
        
        # Get API credentials
        api_base = CONFIG.get_api_base(provider_name)
        api_key = CONFIG.get_api_key(provider_name)
        
        # Call API
        response_stream = call_anthropic_api(translated_request, api_base, api_key)
        
        # Translate response to AWS Event Stream
        for chunk in translate_anthropic_stream(response_stream):
            yield chunk
    
    elif provider_type == 'litellm':
        # For LiteLLM, determine sub-provider from model name
        sub_provider = None
        if 'ollama/' in model_name:
            sub_provider = 'ollama'
        elif 'groq/' in model_name:
            sub_provider = 'groq'
        elif 'openai/' in model_name:
            sub_provider = 'openai'
        elif 'openrouter/' in model_name:
            sub_provider = 'openrouter'
        
        # Get API credentials for sub-provider
        api_base = CONFIG.get_api_base(provider_name, sub_provider)
        api_key = CONFIG.get_api_key(provider_name, sub_provider)
        
        # Check if model uses Anthropic format (Claude models)
        if 'claude' in model_name.lower():
            translated_request = translate_to_anthropic(
                aws_request,
                model=model_name,
                max_tokens=max_tokens
            )
            
            if debug_mode:
                print(f"[Bridge] Translated to Anthropic format (via LiteLLM)")
                print(f"[Bridge] Messages: {len(translated_request['messages'])}")
                if translated_request.get('tools'):
                    print(f"[Bridge] Tools: {len(translated_request['tools'])}")
            
            response_stream = call_litellm_api(translated_request, model_name, api_base, api_key)
            
            # Translate response to AWS Event Stream
            for chunk in translate_anthropic_stream(response_stream):
                yield chunk
        else:
            # Use OpenAI format for other models
            translated_request = translate_to_openai(
                aws_request,
                model=model_name,
                max_tokens=max_tokens
            )
            
            if debug_mode:
                print(f"[Bridge] Translated to OpenAI format (via LiteLLM)")
                print(f"[Bridge] Messages: {len(translated_request['messages'])}")
                if translated_request.get('tools'):
                    print(f"[Bridge] Tools: {len(translated_request['tools'])}")
            
            response_stream = call_litellm_api(translated_request, model_name, api_base, api_key)
            
            # Translate response to AWS Event Stream
            for chunk in translate_openai_stream(response_stream):
                yield chunk
    
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


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
    global CONFIG
    
    if not CONFIG:
        return {'status': 'error', 'message': 'Configuration not loaded'}
    
    return {
        'status': 'ok',
        'enabled_providers': CONFIG.get_enabled_providers(),
        'default_model': CONFIG.get_default_model(),
        'stats': {
            'total_requests': SESSION_STATS['total_requests'],
            'total_tokens': SESSION_STATS['total_tokens'],
            'active_sessions': len(SESSION_STATS['sessions'])
        }
    }


@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    global CONFIG
    
    if not CONFIG:
        return {'error': 'Configuration not loaded'}
    
    return {
        'enabled_providers': CONFIG.get_enabled_providers(),
        'default_model': CONFIG.get_default_model(),
        'available_models': [
            {
                'name': m['name'],
                'provider': m['provider'],
                'aliases': m['aliases'],
                'description': m['description']
            }
            for m in CONFIG.get_all_models()
        ],
        'debug_mode': CONFIG.get('debug.debug_mode_enabled', False)
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


if __name__ == '__main__':
    import os
    from pathlib import Path
    
    # Load config from YAML
    print("\n" + "="*60)
    print("Kiro API Bridge Server")
    print("="*60)
    
    CONFIG = load_config()
    
    if not CONFIG:
        print("\n[ERROR] Failed to load configuration")
        sys.exit(1)
    
    # Print config summary
    CONFIG.print_summary()
    
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
