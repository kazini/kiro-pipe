#!/usr/bin/env python3
"""
AWS Q Request Translator
Converts AWS Q API requests to Anthropic Messages API format
"""

import json
from typing import Dict, Any, List, Optional


def extract_conversation_history(aws_request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract conversation history from AWS Q request
    
    Returns list of messages in Anthropic format
    """
    try:
        conv_state = aws_request.get('conversationState', {})
        history = conv_state.get('history', [])
        
        if not history:
            return []
        
        messages = []
        
        for item in history:
            # User messages
            if 'userInputMessage' in item:
                user_input = item['userInputMessage']
                content = user_input.get('content', '')
                
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
        
        return messages
    except Exception as e:
        print(f"Warning: Failed to extract conversation history: {e}")
        return []


def extract_user_message(aws_request: Dict[str, Any]) -> str:
    """Extract user message from AWS Q request"""
    try:
        conv_state = aws_request.get('conversationState', {})
        current_msg = conv_state.get('currentMessage', {})
        user_input = current_msg.get('userInputMessage', {})
        content = user_input.get('content', '')
        return content
    except Exception as e:
        raise ValueError(f"Failed to extract user message: {e}")


def extract_tools(aws_request: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract tool definitions from AWS Q request and convert to Anthropic format"""
    try:
        conv_state = aws_request.get('conversationState', {})
        current_msg = conv_state.get('currentMessage', {})
        user_input = current_msg.get('userInputMessage', {})
        context = user_input.get('userInputMessageContext', {})
        aws_tools = context.get('tools', [])
        
        if not aws_tools:
            return None
        
        # Convert AWS Q tool format to Anthropic format
        anthropic_tools = []
        for tool in aws_tools:
            # AWS Q wraps tools in toolSpecification
            tool_spec = tool.get('toolSpecification', tool)
            
            anthropic_tool = {
                'name': tool_spec.get('name', ''),
                'description': tool_spec.get('description', ''),
            }
            
            # Convert input schema
            if 'inputSchema' in tool_spec:
                anthropic_tool['input_schema'] = tool_spec['inputSchema']
            
            anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools
    except Exception as e:
        print(f"Warning: Failed to extract tools: {e}")
        return None


def extract_tool_results(aws_request: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Extract tool results from AWS Q request"""
    try:
        conv_state = aws_request.get('conversationState', {})
        current_msg = conv_state.get('currentMessage', {})
        user_input = current_msg.get('userInputMessage', {})
        context = user_input.get('userInputMessageContext', {})
        tool_results = context.get('toolResults', [])
        
        return tool_results if tool_results else None
    except Exception as e:
        print(f"Warning: Failed to extract tool results: {e}")
        return None


def build_anthropic_messages(user_message: str, tool_results: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Build Anthropic messages array from user message and tool results"""
    messages = []
    
    # If there are tool results, we need to include the previous assistant message with tool use
    if tool_results:
        # Add user message with tool results
        content = []
        
        # Add text if present
        if user_message:
            content.append({
                'type': 'text',
                'text': user_message
            })
        
        # Add tool results
        for result in tool_results:
            tool_use_id = result.get('toolUseId', '')
            status = result.get('status', 'success')
            
            # Extract content - AWS Q format has content as array of objects
            result_content = result.get('content', [])
            
            # Convert to string
            if isinstance(result_content, list):
                # Extract text from content array
                text_parts = []
                for item in result_content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, str):
                        text_parts.append(item)
                tool_content = '\n'.join(text_parts) if text_parts else ''
            elif isinstance(result_content, str):
                tool_content = result_content
            else:
                tool_content = str(result_content)
            
            # Handle errors
            if status != 'success':
                error_msg = result.get('error', 'Tool execution failed')
                tool_content = f"Error: {error_msg}"
            
            content.append({
                'type': 'tool_result',
                'tool_use_id': tool_use_id,
                'content': tool_content
            })
        
        messages.append({
            'role': 'user',
            'content': content
        })
    else:
        # Simple user message
        messages.append({
            'role': 'user',
            'content': user_message
        })
    
    return messages


def translate_to_anthropic(aws_request: Dict[str, Any], model: str = 'claude-3-5-sonnet-20241022', 
                          max_tokens: int = 4096) -> Dict[str, Any]:
    """
    Translate AWS Q request to Anthropic Messages API format
    
    Args:
        aws_request: AWS Q API request body
        model: Anthropic model to use
        max_tokens: Maximum tokens in response
    
    Returns:
        Anthropic Messages API request body
    """
    # Extract components
    history = extract_conversation_history(aws_request)
    user_message = extract_user_message(aws_request)
    tools = extract_tools(aws_request)
    tool_results = extract_tool_results(aws_request)
    
    # Build messages from history + current message
    messages = history.copy() if history else []
    
    # Add current message
    current_messages = build_anthropic_messages(user_message, tool_results)
    messages.extend(current_messages)
    
    # Build Anthropic request
    anthropic_request = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': messages,
        'stream': True  # Always stream for real-time responses
    }
    
    # Add tools if present
    if tools:
        anthropic_request['tools'] = tools
    
    return anthropic_request


def translate_to_openai(aws_request: Dict[str, Any], model: str = 'gpt-4', 
                       max_tokens: int = 4096) -> Dict[str, Any]:
    """
    Translate AWS Q request to OpenAI Chat Completions API format
    
    Args:
        aws_request: AWS Q API request body
        model: OpenAI model to use
        max_tokens: Maximum tokens in response
    
    Returns:
        OpenAI Chat Completions API request body
    """
    # Extract components
    user_message = extract_user_message(aws_request)
    tools = extract_tools(aws_request)
    tool_results = extract_tool_results(aws_request)
    
    # Build messages
    messages = []
    
    if tool_results:
        # Add user message with tool results
        # OpenAI format is different - tool results are separate messages
        if user_message:
            messages.append({
                'role': 'user',
                'content': user_message
            })
        
        # Add tool results as tool messages
        for result in tool_results:
            tool_call_id = result.get('toolUseId', '')
            status = result.get('status', 'success')
            
            if status == 'success':
                content = result.get('content', '')
            else:
                content = result.get('error', 'Tool execution failed')
            
            messages.append({
                'role': 'tool',
                'tool_call_id': tool_call_id,
                'content': content
            })
    else:
        # Simple user message
        messages.append({
            'role': 'user',
            'content': user_message
        })
    
    # Build OpenAI request
    openai_request = {
        'model': model,
        'max_tokens': max_tokens,
        'messages': messages,
        'stream': True
    }
    
    # Add tools if present (convert to OpenAI format)
    if tools:
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                'type': 'function',
                'function': {
                    'name': tool['name'],
                    'description': tool.get('description', ''),
                    'parameters': tool.get('input_schema', {})
                }
            })
        openai_request['tools'] = openai_tools
    
    return openai_request


# Test function
if __name__ == '__main__':
    # Example AWS Q request
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
    
    print("AWS Q Request:")
    print(json.dumps(aws_request, indent=2))
    print("\n" + "="*60 + "\n")
    
    # Translate to Anthropic
    anthropic_req = translate_to_anthropic(aws_request)
    print("Anthropic Request:")
    print(json.dumps(anthropic_req, indent=2))
    print("\n" + "="*60 + "\n")
    
    # Translate to OpenAI
    openai_req = translate_to_openai(aws_request)
    print("OpenAI Request:")
    print(json.dumps(openai_req, indent=2))
