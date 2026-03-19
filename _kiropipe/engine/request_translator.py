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
            
            # Assistant messages - DON'T include them here if they have tool use
            # They will be added separately when processing tool results
            elif 'assistantResponseMessage' in item:
                assistant_msg = item['assistantResponseMessage']
                
                # Skip assistant messages with tool use - they'll be added when processing tool results
                if 'toolUse' in assistant_msg and assistant_msg['toolUse']:
                    continue
                
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



def translate_to_anthropic(aws_request: Dict[str, Any], model: str = 'claude-3-5-sonnet-20241022',
                            max_tokens: int = 4096,
                            tool_call_cache: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Translate AWS Q request to Anthropic Messages API format.

    Args:
        aws_request:      AWS Q API request body
        model:            Anthropic model name
        max_tokens:       Maximum tokens in response
        tool_call_cache:  Dict mapping toolUseId -> {name, input} populated by the
                          response translator when tool calls are streamed out.  Used to
                          reconstruct the assistant tool-use message on the return trip
                          because Kiro does NOT put the in-flight assistant turn into
                          history until the full tool round-trip is complete.

    Returns:
        Anthropic Messages API request body
    """
    user_message = extract_user_message(aws_request)
    tools        = extract_tools(aws_request)
    tool_results = extract_tool_results(aws_request)

    conv_state  = aws_request.get('conversationState', {})
    aws_history = conv_state.get('history', [])

    messages: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Walk history and convert every turn, including completed tool-use   #
    # round-trips that are fully committed to history.                    #
    # ------------------------------------------------------------------ #
    i = 0
    while i < len(aws_history):
        item = aws_history[i]

        if 'userInputMessage' in item:
            user_input        = item['userInputMessage']
            text_content      = user_input.get('content', '')
            context           = user_input.get('userInputMessageContext', {})
            hist_tool_results = context.get('toolResults', [])

            if hist_tool_results:
                # Completed tool round-trip — the preceding item must be the
                # assistant message that issued the tool call(s).
                if i > 0 and 'assistantResponseMessage' in aws_history[i - 1]:
                    prev_assistant = aws_history[i - 1]['assistantResponseMessage']
                    tool_uses = prev_assistant.get('toolUse', [])
                    if tool_uses:
                        asst_content = []
                        if prev_assistant.get('content'):
                            asst_content.append({'type': 'text', 'text': prev_assistant['content']})
                        asst_content.extend([_aws_tool_use_to_anthropic_block(tu) for tu in tool_uses])
                        messages.append({'role': 'assistant', 'content': asst_content})

                # Tool results go into a user message as tool_result blocks.
                result_blocks = [_tool_result_to_anthropic_block(r) for r in hist_tool_results]
                user_content: List[Any] = result_blocks
                if text_content:
                    user_content = [{'type': 'text', 'text': text_content}] + result_blocks
                messages.append({'role': 'user', 'content': user_content})

            elif text_content:
                messages.append({'role': 'user', 'content': text_content})

        elif 'assistantResponseMessage' in item:
            assistant_msg = item['assistantResponseMessage']

            if assistant_msg.get('toolUse'):
                # Skip — handled together with the following toolResults turn above.
                i += 1
                continue

            content = assistant_msg.get('content', '')
            if content:
                messages.append({'role': 'assistant', 'content': content})

        i += 1

    # ------------------------------------------------------------------ #
    # Handle the CURRENT tool-results turn.                               #
    #                                                                     #
    # Kiro does not add the in-flight assistant message to history until  #
    # after the round-trip completes, so we use tool_call_cache which the #
    # response translator populates when it streams tool-call events out. #
    # ------------------------------------------------------------------ #
    if tool_results:
        cache = tool_call_cache or {}

        # Reconstruct the assistant message that triggered these tool calls.
        asst_content = []
        for result in tool_results:
            tool_id  = result.get('toolUseId', '')
            cached   = cache.get(tool_id, {})
            input_val = cached.get('input', '{}')
            if isinstance(input_val, str):
                try:
                    input_dict = json.loads(input_val) if input_val else {}
                except json.JSONDecodeError:
                    input_dict = {}
            else:
                input_dict = input_val or {}
            asst_content.append({
                'type':  'tool_use',
                'id':    tool_id,
                'name':  cached.get('name', ''),
                'input': input_dict,
            })

        if asst_content:
            messages.append({'role': 'assistant', 'content': asst_content})

        # Tool results as a user message with tool_result content blocks.
        result_blocks = [_tool_result_to_anthropic_block(r) for r in tool_results]
        user_content_parts: List[Any] = result_blocks
        if user_message:
            user_content_parts = [{'type': 'text', 'text': user_message}] + result_blocks
        messages.append({'role': 'user', 'content': user_content_parts})

    else:
        messages.append({'role': 'user', 'content': user_message})

    # ------------------------------------------------------------------ #
    # Build final request                                                  #
    # ------------------------------------------------------------------ #
    anthropic_request: Dict[str, Any] = {
        'model':      model,
        'max_tokens': max_tokens,
        'messages':   messages,
        'stream':     True,
    }

    if tools:
        anthropic_request['tools'] = tools

    return anthropic_request


def _extract_tool_content(result_content: Any) -> str:
    """
    Safely extract text from an AWS Q tool result content field.
    Handles list-of-dicts, plain string, or anything else.
    """
    if isinstance(result_content, list):
        parts = []
        for item in result_content:
            if isinstance(item, dict) and 'text' in item:
                parts.append(item['text'])
            elif isinstance(item, str):
                parts.append(item)
        return '\n'.join(parts)
    if isinstance(result_content, str):
        return result_content
    return str(result_content)


def _tool_result_to_message(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single AWS Q toolResult entry into an OpenAI role:tool message.
    Handles status check case-insensitively so 'SUCCESS', 'success', 'ok' all pass.
    """
    tool_call_id = result.get('toolUseId', '')
    status = result.get('status', 'success')
    result_content = result.get('content', [])

    content = _extract_tool_content(result_content)

    # Case-insensitive status check — 'SUCCESS', 'Ok', etc. are all fine
    if status.lower() not in ('success', 'ok', ''):
        error_msg = result.get('error', '') or content or 'Tool execution failed'
        content = f"Error: {error_msg}"

    return {
        'role': 'tool',
        'tool_call_id': tool_call_id,
        'content': content,
    }


def _aws_tool_use_to_openai_call(tool_use: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an AWS Q toolUse entry to an OpenAI tool_calls element.
    'input' may arrive as a dict (already parsed) or as a JSON string — normalise to string.
    """
    input_val = tool_use.get('input', '{}')
    if isinstance(input_val, dict):
        arguments = json.dumps(input_val)
    else:
        arguments = input_val if input_val else '{}'

    return {
        'id': tool_use.get('toolUseId', ''),
        'type': 'function',
        'function': {
            'name': tool_use.get('name', ''),
            'arguments': arguments,
        },
    }


def _aws_tool_use_to_anthropic_block(tool_use: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an AWS Q toolUse entry to an Anthropic content block.
    Anthropic requires 'input' to be a dict, never a string.
    """
    input_val = tool_use.get('input', '{}')
    if isinstance(input_val, str):
        try:
            input_dict = json.loads(input_val) if input_val else {}
        except json.JSONDecodeError:
            input_dict = {}
    else:
        input_dict = input_val if input_val else {}

    return {
        'type': 'tool_use',
        'id': tool_use.get('toolUseId', ''),
        'name': tool_use.get('name', ''),
        'input': input_dict,
    }


def _tool_result_to_anthropic_block(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single AWS Q toolResult entry to an Anthropic tool_result content block.
    Status is checked case-insensitively; genuine errors set is_error=True.
    """
    tool_use_id = result.get('toolUseId', '')
    status = result.get('status', 'success')
    result_content = result.get('content', [])

    content = _extract_tool_content(result_content)

    block: Dict[str, Any] = {
        'type': 'tool_result',
        'tool_use_id': tool_use_id,
        'content': content,
    }

    if status.lower() not in ('success', 'ok', ''):
        error_msg = result.get('error', '') or content or 'Tool execution failed'
        block['content'] = f"Error: {error_msg}"
        block['is_error'] = True

    return block


def translate_to_openai(aws_request: Dict[str, Any], model: str = 'gpt-4',
                        max_tokens: int = 4096,
                        tool_call_cache: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Translate AWS Q request to OpenAI Chat Completions API format.

    Args:
        aws_request:      AWS Q API request body
        model:            OpenAI-compatible model name
        max_tokens:       Maximum tokens in response
        tool_call_cache:  Dict mapping toolUseId -> {name, arguments} populated by the
                          response translator when tool calls are streamed out.  Used to
                          reconstruct the assistant tool-call message on the return trip
                          because Kiro does NOT put the in-flight assistant turn into
                          history until the full tool round-trip is complete.

    Returns:
        OpenAI Chat Completions API request body
    """
    user_message = extract_user_message(aws_request)
    tools        = extract_tools(aws_request)
    tool_results = extract_tool_results(aws_request)

    conv_state  = aws_request.get('conversationState', {})
    aws_history = conv_state.get('history', [])

    messages: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Walk history and convert every turn, including completed tool-use   #
    # round-trips that are fully committed to history.                    #
    # ------------------------------------------------------------------ #
    i = 0
    while i < len(aws_history):
        item = aws_history[i]

        if 'userInputMessage' in item:
            user_input      = item['userInputMessage']
            text_content    = user_input.get('content', '')
            context         = user_input.get('userInputMessageContext', {})
            hist_tool_results = context.get('toolResults', [])

            if hist_tool_results:
                # This is a completed tool-result turn in history.
                # The PRECEDING history item should be the assistant message that called the tool.
                if i > 0 and 'assistantResponseMessage' in aws_history[i - 1]:
                    prev_assistant = aws_history[i - 1]['assistantResponseMessage']
                    tool_uses = prev_assistant.get('toolUse', [])
                    if tool_uses:
                        tool_calls = [_aws_tool_use_to_openai_call(tu) for tu in tool_uses]
                        messages.append({
                            'role': 'assistant',
                            'content': None,
                            'tool_calls': tool_calls,
                        })

                for result in hist_tool_results:
                    messages.append(_tool_result_to_message(result))

                # Any free-text that accompanied the tool results
                if text_content:
                    messages.append({'role': 'user', 'content': text_content})
            elif text_content:
                messages.append({'role': 'user', 'content': text_content})

        elif 'assistantResponseMessage' in item:
            assistant_msg = item['assistantResponseMessage']

            if assistant_msg.get('toolUse'):
                # Skip — this assistant tool-call turn is handled together with the
                # following user/toolResults item above.
                i += 1
                continue

            content = assistant_msg.get('content', '')
            if content:
                messages.append({'role': 'assistant', 'content': content})

        i += 1

    # ------------------------------------------------------------------ #
    # Handle the CURRENT tool-results turn.                               #
    #                                                                     #
    # Kiro does not add the in-flight assistant message to history until  #
    # after the round-trip completes, so we cannot find it there.         #
    # Instead we use tool_call_cache which the response translator        #
    # populates when it streams tool-call events back to Kiro.            #
    # ------------------------------------------------------------------ #
    if tool_results:
        cache = tool_call_cache or {}

        # Reconstruct the assistant message that triggered these tool calls.
        tool_calls = []
        for result in tool_results:
            tool_id = result.get('toolUseId', '')
            cached  = cache.get(tool_id, {})
            arguments = cached.get('arguments', '{}')
            if isinstance(arguments, dict):
                arguments = json.dumps(arguments)
            tool_calls.append({
                'id': tool_id,
                'type': 'function',
                'function': {
                    'name': cached.get('name', ''),
                    'arguments': arguments,
                },
            })

        if tool_calls:
            messages.append({
                'role': 'assistant',
                'content': None,
                'tool_calls': tool_calls,
            })

        # Add each tool result as its own role:tool message.
        for result in tool_results:
            messages.append(_tool_result_to_message(result))

        # Append any free-text the user sent alongside the tool results.
        if user_message:
            messages.append({'role': 'user', 'content': user_message})

    else:
        messages.append({'role': 'user', 'content': user_message})

    # ------------------------------------------------------------------ #
    # Build final request                                                  #
    # ------------------------------------------------------------------ #
    openai_request: Dict[str, Any] = {
        'model':      model,
        'max_tokens': max_tokens,
        'messages':   messages,
        'stream':     True,
    }

    if tools:
        openai_request['tools'] = [
            {
                'type': 'function',
                'function': {
                    'name':        t['name'],
                    'description': t.get('description', ''),
                    'parameters':  t.get('input_schema', {}),
                },
            }
            for t in tools
        ]

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
