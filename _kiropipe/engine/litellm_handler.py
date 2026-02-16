#!/usr/bin/env python3
"""
LiteLLM Handler
Deep integration with LiteLLM for universal LLM provider support
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Iterator, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.response_translator import translate_openai_stream


def get_model_max_tokens(model: str) -> Optional[int]:
    """
    Get max tokens for a model from LiteLLM's model cost map
    
    Args:
        model: Model identifier (e.g., "gpt-4", "groq/llama-3.3-70b-versatile")
    
    Returns:
        Max tokens or None if not found
    """
    try:
        from litellm import model_cost
        
        # Try direct lookup
        if model in model_cost:
            model_info = model_cost[model]
            # Check for max_output_tokens first (newer), then max_tokens (legacy)
            return model_info.get('max_output_tokens') or model_info.get('max_tokens')
        
        # Try without provider prefix (e.g., "groq/llama-3.3-70b" -> "llama-3.3-70b")
        if '/' in model:
            model_without_prefix = model.split('/', 1)[1]
            if model_without_prefix in model_cost:
                model_info = model_cost[model_without_prefix]
                return model_info.get('max_output_tokens') or model_info.get('max_tokens')
        
        return None
    except ImportError:
        # LiteLLM not installed
        return None
    except Exception as e:
        print(f"Warning: Failed to get max tokens for {model}: {e}")
        return None


def get_model_cost(model: str, provider: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Get cost information for a model from multiple sources
    
    Priority (for openrouter/* models):
    1. OpenRouter API (highest priority for openrouter models)
    2. LiteLLM model_cost database (fallback)
    
    Priority (for other models):
    1. Free detection (ollama/*, :free suffix, groq free tier)
    2. LiteLLM model_cost database
    3. Pattern inference (fuzzy matching)
    
    Args:
        model: Model identifier (e.g., "gpt-4", "groq/llama-3.3-70b-versatile")
        provider: Optional provider hint (e.g., "ollama", "groq", "openrouter")
    
    Returns:
        Dict with cost info or None:
        {
            'input_cost_per_token': float,
            'output_cost_per_token': float,
            'is_free': bool,
            'source': str  # 'litellm', 'openrouter', 'inferred', 'free'
        }
    """
    try:
        # 1. Check if it's a local/free provider
        if provider == 'ollama' or model.startswith('ollama/'):
            return {
                'input_cost_per_token': 0.0,
                'output_cost_per_token': 0.0,
                'is_free': True,
                'source': 'free'
            }
        
        # 2. Check for :free suffix (OpenRouter free tier)
        if ':free' in model:
            return {
                'input_cost_per_token': 0.0,
                'output_cost_per_token': 0.0,
                'is_free': True,
                'source': 'free'
            }
        
        # 3. Check for Groq free tier models
        # Groq's free tier is truly free with rate limits, not pay-per-token
        # Even though LiteLLM shows costs, these are for paid tier
        if provider == 'groq' or model.startswith('groq/'):
            return {
                'input_cost_per_token': 0.0,
                'output_cost_per_token': 0.0,
                'is_free': True,
                'source': 'free',
                'note': 'Free tier with rate limits (14,400 requests/day, 30/min)'
            }
        
        # 4. For OpenRouter models, prioritize OpenRouter API
        if provider == 'openrouter' or model.startswith('openrouter/'):
            try:
                import requests
                response = requests.get('https://openrouter.ai/api/v1/models', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Find matching model
                    model_to_match = model.replace('openrouter/', '')
                    for or_model in data.get('data', []):
                        if or_model['id'] == model_to_match or or_model['id'] == model:
                            pricing = or_model.get('pricing', {})
                            input_cost = float(pricing.get('prompt', 0))
                            output_cost = float(pricing.get('completion', 0))
                            
                            return {
                                'input_cost_per_token': input_cost,
                                'output_cost_per_token': output_cost,
                                'is_free': (input_cost == 0 and output_cost == 0),
                                'source': 'openrouter'
                            }
            except Exception as e:
                # Connection failed - will try LiteLLM fallback below
                print(f"Warning: OpenRouter API failed for {model}, trying fallback: {e}")
        
        # 5. Try LiteLLM model_cost database
        try:
            from litellm import model_cost
            
            # Try direct lookup
            if model in model_cost:
                model_info = model_cost[model]
                input_cost = model_info.get('input_cost_per_token', 0)
                output_cost = model_info.get('output_cost_per_token', 0)
                
                if input_cost or output_cost:
                    return {
                        'input_cost_per_token': input_cost,
                        'output_cost_per_token': output_cost,
                        'is_free': (input_cost == 0 and output_cost == 0),
                        'source': 'litellm'
                    }
            
            # Try without provider prefix
            if '/' in model:
                model_without_prefix = model.split('/', 1)[1]
                if model_without_prefix in model_cost:
                    model_info = model_cost[model_without_prefix]
                    input_cost = model_info.get('input_cost_per_token', 0)
                    output_cost = model_info.get('output_cost_per_token', 0)
                    
                    if input_cost or output_cost:
                        return {
                            'input_cost_per_token': input_cost,
                            'output_cost_per_token': output_cost,
                            'is_free': (input_cost == 0 and output_cost == 0),
                            'source': 'litellm'
                        }
        except ImportError:
            pass
        
        # 6. Try to infer from cloud provider patterns
        # If model name matches a known cloud provider pattern, try to find base model cost
        if '/' in model:
            provider_prefix, base_model = model.split('/', 1)
            
            # Try to find the base model in LiteLLM (e.g., groq/llama-3.3-70b -> llama-3.3-70b)
            try:
                from litellm import model_cost
                
                # Look for similar models in the database
                for known_model, info in model_cost.items():
                    # Match by base model name (fuzzy)
                    if base_model.lower() in known_model.lower() or known_model.lower() in base_model.lower():
                        input_cost = info.get('input_cost_per_token', 0)
                        output_cost = info.get('output_cost_per_token', 0)
                        
                        if input_cost or output_cost:
                            return {
                                'input_cost_per_token': input_cost,
                                'output_cost_per_token': output_cost,
                                'is_free': False,
                                'source': 'inferred'
                            }
            except ImportError:
                pass
        
        return None
    except Exception as e:
        print(f"Warning: Failed to get cost for {model}: {e}")
        return None


def extract_conversation_from_aws(aws_request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract conversation history from AWS Q request and convert to OpenAI format
    
    Args:
        aws_request: AWS Q API request body
    
    Returns:
        List of messages in OpenAI format
    """
    messages = []
    
    try:
        conv_state = aws_request.get('conversationState', {})
        history = conv_state.get('history', [])
        
        for item in history:
            # User messages
            if 'userInputMessage' in item:
                user_msg = item['userInputMessage']
                content = user_msg.get('content', '')
                if content:
                    messages.append({
                        'role': 'user',
                        'content': content
                    })
            
            # Assistant messages
            elif 'assistantResponseMessage' in item:
                assistant_msg = item['assistantResponseMessage']
                content = assistant_msg.get('content', '')
                if content:
                    messages.append({
                        'role': 'assistant',
                        'content': content
                    })
        
        # Add current message
        current_msg = conv_state.get('currentMessage', {})
        if 'userInputMessage' in current_msg:
            user_input = current_msg['userInputMessage']
            content = user_input.get('content', '')
            if content:
                messages.append({
                    'role': 'user',
                    'content': content
                })
    
    except Exception as e:
        print(f"Warning: Failed to extract conversation history: {e}")
        # Fallback to just current message
        try:
            content = (
                aws_request.get('conversationState', {})
                .get('currentMessage', {})
                .get('userInputMessage', {})
                .get('content', '')
            )
            if content:
                messages = [{'role': 'user', 'content': content}]
        except:
            pass
    
    return messages


def extract_tools_from_aws(aws_request: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Extract tool definitions from AWS Q request and convert to OpenAI format
    
    Args:
        aws_request: AWS Q API request body
    
    Returns:
        List of tools in OpenAI format, or None if no tools
    """
    try:
        conv_state = aws_request.get('conversationState', {})
        current_msg = conv_state.get('currentMessage', {})
        context = current_msg.get('userInputMessageContext', {})
        aws_tools = context.get('tools', [])
        
        if not aws_tools:
            return None
        
        # Convert AWS Q tool format to OpenAI format
        openai_tools = []
        for tool in aws_tools:
            # AWS Q wraps tools in toolSpecification
            tool_spec = tool.get('toolSpecification', tool)
            
            openai_tool = {
                'type': 'function',
                'function': {
                    'name': tool_spec.get('name', ''),
                    'description': tool_spec.get('description', ''),
                    'parameters': tool_spec.get('inputSchema', {})
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    except Exception as e:
        print(f"Warning: Failed to extract tools: {e}")
        return None


def call_litellm_streaming(
    model: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> tuple[Iterator[Dict[str, Any]], Dict[str, str]]:
    """
    Call LiteLLM with streaming and return OpenAI-compatible chunks + headers
    
    Args:
        model: Model identifier (e.g., "gpt-4", "claude-3-sonnet", "ollama/llama3")
        messages: List of messages in OpenAI format
        tools: Optional list of tools in OpenAI format
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        api_base: Optional custom API base URL
        api_key: Optional API key
        **kwargs: Additional parameters to pass to LiteLLM
    
    Returns:
        Tuple of (streaming chunks iterator, response headers dict)
    """
    try:
        from litellm import completion
    except ImportError:
        raise ImportError(
            "LiteLLM not installed. Install with: pip install litellm\n"
            "Or run: python kiropipe.py (it will prompt to install dependencies)"
        )
    
    # Build request parameters
    request_params = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': temperature,
        'stream': True,
        **kwargs
    }
    
    # Add tools if provided
    if tools:
        request_params['tools'] = tools
    
    # Add API base if provided
    if api_base:
        request_params['api_base'] = api_base
    
    # Add API key if provided
    if api_key:
        request_params['api_key'] = api_key
    
    # Call LiteLLM
    response_stream = completion(**request_params)
    
    # Extract headers from first chunk (if available)
    headers = {}
    
    def stream_with_header_capture():
        """Generator that captures headers from first chunk"""
        nonlocal headers
        first_chunk = True
        
        for chunk in response_stream:
            # Try to extract headers from first chunk
            if first_chunk:
                first_chunk = False
                # LiteLLM may include response headers in _hidden_params
                if hasattr(chunk, '_hidden_params') and 'additional_headers' in chunk._hidden_params:
                    headers.update(chunk._hidden_params['additional_headers'])
                # Or in response_ms metadata
                if hasattr(chunk, '_response_ms'):
                    # Headers might be in the underlying response object
                    pass
            
            # Convert LiteLLM chunks to dicts
            if hasattr(chunk, 'model_dump'):
                yield chunk.model_dump()
            elif hasattr(chunk, 'dict'):
                yield chunk.dict()
            else:
                yield dict(chunk)
    
    return stream_with_header_capture(), headers


def aws_to_litellm_to_aws(
    aws_request: Dict[str, Any],
    model: str,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    max_retries: int = 3,
    **kwargs
) -> tuple[bytes, Dict[str, str]]:
    """
    Complete translation pipeline: AWS Q → LiteLLM → AWS Event Stream
    
    Args:
        aws_request: AWS Q API request body
        model: LiteLLM model identifier
        api_base: Optional custom API base URL
        api_key: Optional API key
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        max_retries: Maximum number of retry attempts for rate limits
        **kwargs: Additional parameters to pass to LiteLLM
    
    Returns:
        Tuple of (AWS Event Stream binary response, response headers dict)
    """
    # Step 1: Extract conversation and tools from AWS Q format
    messages = extract_conversation_from_aws(aws_request)
    tools = extract_tools_from_aws(aws_request)
    
    if not messages:
        raise ValueError("No messages found in AWS Q request")
    
    # Step 2: Call LiteLLM with streaming and retry logic
    headers_captured = {}
    
    try:
        from litellm import completion
        from litellm.exceptions import RateLimitError
        import time
        import re
        
        # Build request parameters
        request_params = {
            'model': model,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': True,
            **kwargs
        }
        
        if tools:
            request_params['tools'] = tools
        if api_base:
            request_params['api_base'] = api_base
        if api_key:
            request_params['api_key'] = api_key
        
        # Retry logic for rate limits
        response_stream = None
        for attempt in range(max_retries):
            try:
                # Call LiteLLM
                response_stream = completion(**request_params)
                break  # Success - exit retry loop
                
            except RateLimitError as e:
                error_msg = str(e)
                
                # Extract wait time from error message
                wait_time = None
                # Pattern: "Please try again in 8.19s"
                match = re.search(r'try again in ([\d.]+)s', error_msg)
                if match:
                    wait_time = float(match.group(1))
                else:
                    # Exponential backoff if no wait time specified
                    wait_time = 2 ** attempt
                
                if attempt < max_retries - 1:
                    print(f"Rate limited. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    # Last attempt failed - re-raise with user-friendly message
                    print(f"Rate limit exceeded after {max_retries} attempts")
                    raise RateLimitError(
                        f"Rate limit exceeded. The model is receiving too many requests. "
                        f"Please wait a moment and try again. Original error: {error_msg}"
                    )
        
        if response_stream is None:
            raise Exception("Failed to get response from LiteLLM after retries")
        
        # Try to extract headers from the response object
        # LiteLLM wraps the underlying HTTP response
        try:
            if hasattr(response_stream, '_response'):
                underlying_response = response_stream._response
                if hasattr(underlying_response, 'headers'):
                    headers_captured = dict(underlying_response.headers)
        except Exception as header_err:
            # Silently fail header extraction - not critical
            pass
        
        # Convert stream to list to capture all chunks
        chunks = []
        for chunk in response_stream:
            if hasattr(chunk, 'model_dump'):
                chunks.append(chunk.model_dump())
            elif hasattr(chunk, 'dict'):
                chunks.append(chunk.dict())
            else:
                chunks.append(dict(chunk))
        
        # Step 3: Translate OpenAI stream to AWS Event Stream
        aws_binary = b''.join(translate_openai_stream(iter(chunks)))
        
        return aws_binary, headers_captured
        
    except Exception as e:
        print(f"Warning: Failed to capture headers: {e}")
        # Fallback: just return empty headers
        litellm_stream, _ = call_litellm_streaming(
            model=model,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            api_base=api_base,
            api_key=api_key,
            **kwargs
        )
        aws_binary = b''.join(translate_openai_stream(litellm_stream))
        return aws_binary, {}


# Provider-specific helpers

def get_litellm_model_name(provider: str, model_name: str) -> str:
    """
    Convert provider + model name to LiteLLM format
    
    Examples:
        - ollama + llama3 → ollama/llama3
        - groq + llama-3.1-70b → groq/llama-3.1-70b
        - openai + gpt-4 → gpt-4 (no prefix needed)
        - anthropic + claude-3-sonnet → anthropic/claude-3-sonnet
    
    Args:
        provider: Provider name (e.g., "ollama", "groq", "openai")
        model_name: Model name
    
    Returns:
        LiteLLM-formatted model identifier
    """
    # OpenAI models don't need prefix
    if provider.lower() in ['openai', 'azure', 'azure_ai']:
        return model_name
    
    # Most providers need prefix
    if '/' not in model_name:
        return f"{provider}/{model_name}"
    
    return model_name


def get_provider_config(provider_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract provider configuration from config dict
    
    Args:
        provider_name: Provider name (e.g., "ollama", "groq")
        config: Full provider configuration
    
    Returns:
        Provider-specific config with api_base and api_key
    """
    provider_config = config.get(provider_name, {})
    
    return {
        'api_base': provider_config.get('api_base'),
        'api_key': provider_config.get('api_key'),
        'models': provider_config.get('models', [])
    }


# Test function
if __name__ == '__main__':
    print("LiteLLM Handler Test\n")
    print("="*60)
    
    # Test 1: AWS Q to OpenAI format conversion
    print("\nTest 1: AWS Q → OpenAI Format")
    print("-"*60)
    
    aws_request = {
        'conversationState': {
            'history': [
                {
                    'userInputMessage': {
                        'content': 'Hello!'
                    }
                },
                {
                    'assistantResponseMessage': {
                        'content': 'Hi there! How can I help?'
                    }
                }
            ],
            'currentMessage': {
                'userInputMessage': {
                    'content': 'What is 2+2?'
                }
            }
        }
    }
    
    messages = extract_conversation_from_aws(aws_request)
    print(f"✓ Extracted {len(messages)} messages:")
    for i, msg in enumerate(messages, 1):
        print(f"  {i}. {msg['role']}: {msg['content']}")
    
    # Test 2: Tool extraction
    print("\n" + "="*60)
    print("\nTest 2: Tool Extraction")
    print("-"*60)
    
    aws_request_with_tools = {
        'conversationState': {
            'currentMessage': {
                'userInputMessage': {
                    'content': 'Read file.txt'
                },
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
    
    tools = extract_tools_from_aws(aws_request_with_tools)
    if tools:
        print(f"✓ Extracted {len(tools)} tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  {i}. {tool['function']['name']}: {tool['function']['description']}")
    else:
        print("✗ No tools extracted")
    
    # Test 3: Model name formatting
    print("\n" + "="*60)
    print("\nTest 3: Model Name Formatting")
    print("-"*60)
    
    test_cases = [
        ('ollama', 'llama3', 'ollama/llama3'),
        ('groq', 'llama-3.1-70b', 'groq/llama-3.1-70b'),
        ('openai', 'gpt-4', 'gpt-4'),
        ('anthropic', 'claude-3-sonnet', 'anthropic/claude-3-sonnet'),
    ]
    
    for provider, model, expected in test_cases:
        result = get_litellm_model_name(provider, model)
        status = "✓" if result == expected else "✗"
        print(f"{status} {provider} + {model} → {result}")
    
    # Test 4: Max tokens lookup
    print("\n" + "="*60)
    print("\nTest 4: Max Tokens Lookup (requires LiteLLM)")
    print("-"*60)
    
    test_models = [
        'gpt-4',
        'groq/llama-3.3-70b-versatile',
        'claude-3-5-sonnet-20241022',
        'ollama/llama3.2',
    ]
    
    for model in test_models:
        max_tokens = get_model_max_tokens(model)
        if max_tokens:
            print(f"✓ {model}: {max_tokens:,} tokens")
        else:
            print(f"⚠ {model}: Not found in LiteLLM cost map")
    
    print("\n" + "="*60)
    print("\n✓ LiteLLM handler tests complete!")
