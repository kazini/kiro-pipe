#!/usr/bin/env python3
"""
Response Translator
Converts LLM API responses (Anthropic/OpenAI) to AWS Event Stream format
"""

import json
import sys
from pathlib import Path
from typing import Iterator, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.event_stream_encoder import (
    encode_text_chunk,
    encode_tool_use_chunk,
    encode_metering,
    encode_context_usage
)


def translate_anthropic_stream(response_stream: Iterator[Dict[str, Any]], 
                              include_usage: bool = True,
                              usage_callback: Optional[callable] = None) -> Iterator[bytes]:
    """
    Translate Anthropic streaming response to AWS Event Stream format
    
    Args:
        response_stream: Iterator of Anthropic SSE events
        include_usage: Whether to include usage metrics
        usage_callback: Optional callback function(input_tokens, output_tokens)
    
    Yields:
        AWS Event Stream binary chunks
    """
    tool_use_buffer = {}  # Buffer for accumulating tool use chunks
    tool_use_index = {}  # Map index to tool ID
    total_input_tokens = 0
    total_output_tokens = 0
    has_usage_data = False  # Track if we got usage data
    
    for event in response_stream:
        event_type = event.get('type')
        
        if event_type == 'message_start':
            # Extract usage from message start
            message = event.get('message', {})
            usage = message.get('usage', {})
            if usage:
                total_input_tokens = usage.get('input_tokens', 0)
                has_usage_data = True
        
        elif event_type == 'content_block_start':
            # Check if it's a tool use block
            content_block = event.get('content_block', {})
            block_index = event.get('index', 0)
            
            if content_block.get('type') == 'tool_use':
                tool_id = content_block.get('id', '')
                tool_name = content_block.get('name', '')
                tool_use_buffer[tool_id] = {
                    'name': tool_name,
                    'input': ''
                }
                tool_use_index[block_index] = tool_id
        
        elif event_type == 'content_block_delta':
            delta = event.get('delta', {})
            delta_type = delta.get('type')
            
            if delta_type == 'text_delta':
                # Text content - encode and yield
                text = delta.get('text', '')
                if text:
                    yield encode_text_chunk(text)
            
            elif delta_type == 'input_json_delta':
                # Tool use input chunk
                index = event.get('index', 0)
                partial_json = delta.get('partial_json', '')
                
                # Find the tool use ID for this index
                if index in tool_use_index:
                    tool_id = tool_use_index[index]
                    tool_use_buffer[tool_id]['input'] += partial_json
                    
                    # Yield tool use chunk
                    yield encode_tool_use_chunk(
                        tool_use_buffer[tool_id]['name'],
                        tool_id,
                        partial_json
                    )
        
        elif event_type == 'content_block_stop':
            # Tool use complete - send final empty chunk with stop=True
            block_index = event.get('index', 0)
            
            if block_index in tool_use_index:
                tool_id = tool_use_index[block_index]
                if tool_id in tool_use_buffer:
                    yield encode_tool_use_chunk(
                        tool_use_buffer[tool_id]['name'],
                        tool_id,
                        '',
                        is_final=True  # Mark as final chunk
                    )
                    # Clear from buffers
                    tool_use_buffer.pop(tool_id, None)
                    tool_use_index.pop(block_index, None)
        
        elif event_type == 'message_delta':
            # Extract output tokens
            delta = event.get('delta', {})
            usage = event.get('usage', {})
            if usage:
                total_output_tokens = usage.get('output_tokens', 0)
                has_usage_data = True
        
        elif event_type == 'message_stop':
            # End of message - send usage metrics only if we have data
            if include_usage and has_usage_data and (total_input_tokens or total_output_tokens):
                # Call usage callback if provided
                if usage_callback:
                    try:
                        usage_callback(total_input_tokens, total_output_tokens)
                    except Exception as e:
                        print(f"[Warning] Usage callback failed: {e}")
                
                # Calculate approximate credit usage (rough estimate)
                # AWS Q seems to use ~0.2-0.3 credits per interaction
                total_tokens = total_input_tokens + total_output_tokens
                credits = total_tokens / 10000  # Rough approximation
                
                yield encode_metering(credits)
                
                # Context usage (estimate based on input tokens)
                if total_input_tokens > 0:
                    # Assume 200k context window
                    context_pct = (total_input_tokens / 200000) * 100
                    yield encode_context_usage(context_pct)


def translate_openai_stream(response_stream: Iterator[Dict[str, Any]],
                           include_usage: bool = True,
                           usage_callback: Optional[callable] = None,
                           tool_calls_out: Optional[Dict[str, Any]] = None) -> Iterator[bytes]:
    """
    Translate OpenAI streaming response to AWS Event Stream format

    Args:
        response_stream:  Iterator of OpenAI SSE events
        include_usage:    Whether to include usage metrics
        usage_callback:   Optional callback function(input_tokens, output_tokens)
        tool_calls_out:   Optional dict populated with {toolUseId: {name, arguments}}
                          for every tool call streamed out.  The caller (KiroInterceptor)
                          stores this so it can reconstruct the assistant tool-call
                          message on the next round-trip.

    Yields:
        AWS Event Stream binary chunks
    """
    tool_calls_buffer = {}  # Buffer for accumulating tool calls
    total_prompt_tokens = 0
    total_completion_tokens = 0
    has_usage_data = False  # Track if we got usage data
    
    for chunk in response_stream:
        choices = chunk.get('choices', [])
        if not choices:
            continue
        
        choice = choices[0]
        delta = choice.get('delta', {})
        
        # Handle text content
        if 'content' in delta and delta['content']:
            yield encode_text_chunk(delta['content'])
        
        # Handle tool calls
        if 'tool_calls' in delta:
            for tool_call in delta['tool_calls']:
                index = tool_call.get('index', 0)
                tool_id = tool_call.get('id', '')
                
                # Initialize buffer for this tool call
                if index not in tool_calls_buffer:
                    tool_calls_buffer[index] = {
                        'id': tool_id,
                        'name': '',
                        'arguments': ''
                    }
                
                # Update name if present
                function = tool_call.get('function', {})
                if 'name' in function:
                    tool_calls_buffer[index]['name'] = function['name']
                
                # Accumulate arguments
                if 'arguments' in function:
                    args_chunk = function['arguments']
                    tool_calls_buffer[index]['arguments'] += args_chunk
                    
                    # Yield tool use chunk
                    yield encode_tool_use_chunk(
                        tool_calls_buffer[index]['name'],
                        tool_calls_buffer[index]['id'],
                        args_chunk
                    )
        
        # Check for finish
        finish_reason = choice.get('finish_reason')
        if finish_reason:
            # Send final empty chunks for any tool calls with stop=True
            for tool_call in tool_calls_buffer.values():
                yield encode_tool_use_chunk(
                    tool_call['name'],
                    tool_call['id'],
                    '',
                    is_final=True  # Mark as final chunk
                )

            # Populate tool_calls_out so the interceptor can cache name+arguments
            # keyed by toolUseId, enabling reconstruction of the assistant message
            # on the next request when Kiro sends back tool results.
            if tool_calls_out is not None:
                for tool_call in tool_calls_buffer.values():
                    tool_id = tool_call['id']
                    tool_calls_out[tool_id] = {
                        'name':      tool_call['name'],
                        'arguments': tool_call['arguments'],
                    }
            
            # Check for usage in the chunk
            if include_usage:
                usage = chunk.get('usage', {})
                if usage:
                    total_prompt_tokens = usage.get('prompt_tokens', 0)
                    total_completion_tokens = usage.get('completion_tokens', 0)
                    total_tokens = usage.get('total_tokens', 0)
                    has_usage_data = True
                    
                    # Call usage callback if provided
                    if usage_callback:
                        try:
                            usage_callback(total_prompt_tokens, total_completion_tokens)
                        except Exception as e:
                            print(f"[Warning] Usage callback failed: {e}")
                    
                    # Only send metering if we have actual usage data
                    credits = total_tokens / 10000
                    yield encode_metering(credits)
                    
                    if total_prompt_tokens > 0:
                        context_pct = (total_prompt_tokens / 200000) * 100
                        yield encode_context_usage(context_pct)
    
    # If we finished without usage data, don't send metering events
    # This prevents showing "Credits used" when the provider doesn't report usage


def parse_anthropic_sse(sse_text: str) -> Iterator[Dict[str, Any]]:
    """Parse Anthropic Server-Sent Events format"""
    for line in sse_text.split('\n'):
        line = line.strip()
        if line.startswith('data: '):
            data = line[6:]  # Remove 'data: ' prefix
            if data and data != '[DONE]':
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    pass


def parse_openai_sse(sse_text: str) -> Iterator[Dict[str, Any]]:
    """Parse OpenAI Server-Sent Events format"""
    for line in sse_text.split('\n'):
        line = line.strip()
        if line.startswith('data: '):
            data = line[6:]  # Remove 'data: ' prefix
            if data and data != '[DONE]':
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    pass


# Test function
if __name__ == '__main__':
    print("Response Translator Test\n")
    print("="*60)
    
    # Simulate Anthropic streaming response
    print("\nTest 1: Anthropic Text Response")
    print("-"*60)
    
    anthropic_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 100}}},
        {'type': 'content_block_start', 'content_block': {'type': 'text'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': 'Hello'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': ' world'}},
        {'type': 'content_block_delta', 'delta': {'type': 'text_delta', 'text': '!'}},
        {'type': 'content_block_stop'},
        {'type': 'message_delta', 'usage': {'output_tokens': 50}},
        {'type': 'message_stop'}
    ]
    
    aws_stream = b''.join(translate_anthropic_stream(iter(anthropic_events)))
    print(f"Generated {len(aws_stream)} bytes of AWS Event Stream data")
    print(f"First 100 bytes (hex): {aws_stream[:100].hex()}")
    
    # Test with decoder
    from engine.decode_event_stream import decode_event_stream
    events = decode_event_stream(aws_stream)
    print(f"\nDecoded {len(events)} events:")
    for i, event in enumerate(events, 1):
        event_type = event['headers'].get(':event-type')
        print(f"  {i}. {event_type}: {event['payload']}")
    
    print("\n" + "="*60)
    print("\nTest 2: Anthropic Tool Use Response")
    print("-"*60)
    
    anthropic_tool_events = [
        {'type': 'message_start', 'message': {'usage': {'input_tokens': 150}}},
        {'type': 'content_block_start', 'content_block': {'type': 'tool_use', 'id': 'tool_123', 'name': 'readFile'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': '{"path"'}},
        {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': ': "test.py"}'}},
        {'type': 'content_block_stop'},
        {'type': 'message_delta', 'usage': {'output_tokens': 30}},
        {'type': 'message_stop'}
    ]
    
    aws_tool_stream = b''.join(translate_anthropic_stream(iter(anthropic_tool_events)))
    print(f"Generated {len(aws_tool_stream)} bytes of AWS Event Stream data")
    
    tool_events = decode_event_stream(aws_tool_stream)
    print(f"\nDecoded {len(tool_events)} events:")
    for i, event in enumerate(tool_events, 1):
        event_type = event['headers'].get(':event-type')
        print(f"  {i}. {event_type}: {event['payload']}")
    
    print("\n" + "="*60)
    print("\n✓ Response translator tests complete!")
