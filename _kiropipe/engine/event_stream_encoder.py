#!/usr/bin/env python3
"""
AWS Event Stream Encoder
Generates binary event stream responses matching AWS Q format
"""

import struct
import json
from typing import Dict, Any, List


def calculate_crc32(data: bytes) -> int:
    """Calculate CRC32 checksum"""
    import zlib
    return zlib.crc32(data) & 0xffffffff


def encode_header(name: str, value: str, value_type: int = 7) -> bytes:
    """
    Encode a single header
    
    Args:
        name: Header name (e.g., ':event-type')
        value: Header value (e.g., 'assistantResponseEvent')
        value_type: Header value type (7 = string)
    
    Returns:
        Encoded header bytes
    """
    name_bytes = name.encode('utf-8')
    value_bytes = value.encode('utf-8')
    
    header = bytearray()
    header.append(len(name_bytes))  # Name length (1 byte)
    header.extend(name_bytes)  # Name
    header.append(value_type)  # Value type (1 byte)
    header.extend(struct.pack('>H', len(value_bytes)))  # Value length (2 bytes, big-endian)
    header.extend(value_bytes)  # Value
    
    return bytes(header)


def encode_event(event_type: str, payload: Dict[str, Any], content_type: str = "application/json") -> bytes:
    """
    Encode a single event in AWS Event Stream format
    
    Args:
        event_type: Event type (e.g., 'assistantResponseEvent', 'toolUseEvent')
        payload: Event payload (will be JSON encoded)
        content_type: Content type (default: 'application/json')
    
    Returns:
        Complete encoded event as bytes
    """
    # Encode headers
    headers = bytearray()
    headers.extend(encode_header(':event-type', event_type))
    headers.extend(encode_header(':content-type', content_type))
    headers.extend(encode_header(':message-type', 'event'))
    
    # Encode payload
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    # Calculate lengths
    headers_length = len(headers)
    total_length = 12 + headers_length + len(payload_bytes) + 4  # prelude + headers + payload + message CRC
    
    # Build prelude
    prelude = struct.pack('>I', total_length)  # Total length (4 bytes)
    prelude += struct.pack('>I', headers_length)  # Headers length (4 bytes)
    prelude_crc = calculate_crc32(prelude)
    prelude += struct.pack('>I', prelude_crc)  # Prelude CRC (4 bytes)
    
    # Build complete message
    message = bytearray()
    message.extend(prelude)
    message.extend(headers)
    message.extend(payload_bytes)
    
    # Calculate and append message CRC
    message_crc = calculate_crc32(bytes(message))
    message.extend(struct.pack('>I', message_crc))
    
    return bytes(message)


def encode_text_chunk(text: str) -> bytes:
    """
    Encode a text chunk as assistantResponseEvent
    
    Args:
        text: Text content to encode
    
    Returns:
        Encoded event bytes
    """
    return encode_event('assistantResponseEvent', {'content': text})


def encode_tool_use_chunk(tool_name: str, tool_id: str, input_chunk: str, is_final: bool = False) -> bytes:
    """
    Encode a tool use chunk as toolUseEvent
    
    Args:
        tool_name: Tool name
        tool_id: Tool use ID
        input_chunk: Partial JSON input string
        is_final: Whether this is the final chunk (adds 'stop': true)
    
    Returns:
        Encoded event bytes
    """
    payload = {
        'name': tool_name,
        'toolUseId': tool_id,
        'input': input_chunk
    }
    
    # Add stop field for final chunk (when input is empty and is_final is True)
    if is_final or (input_chunk == '' and is_final is None):
        # If input is empty, this is likely a stop event
        # AWS Q format uses 'stop': true for final tool event
        payload['stop'] = True
    
    return encode_event('toolUseEvent', payload)


def encode_metering(usage: float, unit: str = 'credit', unit_plural: str = 'credits') -> bytes:
    """
    Encode usage metering event
    
    Args:
        usage: Usage amount
        unit: Unit name (singular)
        unit_plural: Unit name (plural)
    
    Returns:
        Encoded event bytes
    """
    payload = {
        'unit': unit,
        'unitPlural': unit_plural,
        'usage': usage
    }
    return encode_event('meteringEvent', payload)


def encode_context_usage(percentage: float) -> bytes:
    """
    Encode context usage event
    
    Args:
        percentage: Context usage percentage
    
    Returns:
        Encoded event bytes
    """
    payload = {'contextUsagePercentage': percentage}
    return encode_event('contextUsageEvent', payload)


def encode_streaming_response(text_chunks: List[str], usage: float = 0.0, context_pct: float = 0.0) -> bytes:
    """
    Encode a complete streaming response with text chunks
    
    Args:
        text_chunks: List of text chunks to stream
        usage: Usage amount (optional)
        context_pct: Context usage percentage (optional)
    
    Returns:
        Complete encoded response as bytes
    """
    response = bytearray()
    
    # Encode text chunks
    for chunk in text_chunks:
        response.extend(encode_text_chunk(chunk))
    
    # Add metering if provided
    if usage > 0:
        response.extend(encode_metering(usage))
    
    # Add context usage if provided
    if context_pct > 0:
        response.extend(encode_context_usage(context_pct))
    
    return bytes(response)


# Test function
if __name__ == '__main__':
    # Test encoding
    print("Testing AWS Event Stream Encoder\n")
    
    # Test 1: Simple text chunk
    chunk = encode_text_chunk("Hello, world!")
    print(f"Text chunk encoded: {len(chunk)} bytes")
    print(f"First 50 bytes (hex): {chunk[:50].hex()}\n")
    
    # Test 2: Complete response
    chunks = ["Hello", ", ", "world", "!"]
    response = encode_streaming_response(chunks, usage=0.5, context_pct=25.0)
    print(f"Complete response encoded: {len(response)} bytes")
    print(f"First 100 bytes (hex): {response[:100].hex()}\n")
    
    # Test 3: Tool use
    tool_event = encode_tool_use_chunk("readFile", "tool_123", '{"path": "test.py"}')
    print(f"Tool use event encoded: {len(tool_event)} bytes")
    print(f"First 50 bytes (hex): {tool_event[:50].hex()}\n")
    
    print("Encoding tests complete!")
