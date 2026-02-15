#!/usr/bin/env python3
"""
Decode AWS Event Stream binary format
"""

import struct
import json
from pathlib import Path

def decode_event_stream(data):
    """Decode AWS event-stream binary format"""
    events = []
    offset = 0
    
    while offset < len(data):
        if offset + 12 > len(data):
            break
            
        # Read prelude (12 bytes)
        total_length = struct.unpack('>I', data[offset:offset+4])[0]
        headers_length = struct.unpack('>I', data[offset+4:offset+8])[0]
        prelude_crc = struct.unpack('>I', data[offset+8:offset+12])[0]
        
        if offset + total_length > len(data):
            break
        
        # Read headers
        headers_start = offset + 12
        headers_end = headers_start + headers_length
        headers_data = data[headers_start:headers_end]
        
        # Parse headers
        headers = {}
        h_offset = 0
        while h_offset < len(headers_data):
            # Header name length (1 byte)
            name_len = headers_data[h_offset]
            h_offset += 1
            
            # Header name
            name = headers_data[h_offset:h_offset+name_len].decode('utf-8')
            h_offset += name_len
            
            # Header value type (1 byte)
            value_type = headers_data[h_offset]
            h_offset += 1
            
            # Header value length (2 bytes)
            value_len = struct.unpack('>H', headers_data[h_offset:h_offset+2])[0]
            h_offset += 2
            
            # Header value
            value = headers_data[h_offset:h_offset+value_len].decode('utf-8')
            h_offset += value_len
            
            headers[name] = value
        
        # Read payload
        payload_start = headers_end
        payload_end = offset + total_length - 4  # -4 for message CRC
        payload = data[payload_start:payload_end]
        
        # Try to decode payload as JSON
        try:
            payload_json = json.loads(payload.decode('utf-8'))
        except:
            payload_json = payload.decode('utf-8', errors='ignore')
        
        events.append({
            'headers': headers,
            'payload': payload_json
        })
        
        # Move to next event
        offset += total_length
    
    return events

def main():
    """Decode all binary response files"""
    # Get paths relative to script location
    script_dir = Path(__file__).parent.parent  # Go up to _kiropipe
    responses_dir = script_dir / 'debug_logs' / 'interactions' / 'responses'
    binary_files = sorted(responses_dir.glob('response_binary_*.bin'))
    
    if not binary_files:
        print("No binary response files found.")
        return
    
    for bf in binary_files:
        print(f"\n{'='*60}")
        print(f"Decoding: {bf.name}")
        print(f"{'='*60}\n")
        
        with open(bf, 'rb') as f:
            data = f.read()
        
        print(f"File size: {len(data)} bytes")
        print(f"First 100 bytes (hex): {data[:100].hex()}\n")
        
        try:
            events = decode_event_stream(data)
            print(f"Decoded {len(events)} events:\n")
            
            for i, event in enumerate(events, 1):
                print(f"Event #{i}:")
                print(f"  Headers: {event['headers']}")
                
                if isinstance(event['payload'], dict):
                    payload_str = json.dumps(event['payload'], indent=2)
                    if len(payload_str) > 1000:
                        print(f"  Payload (truncated):\n{payload_str[:1000]}...")
                    else:
                        print(f"  Payload:\n{payload_str}")
                else:
                    if len(str(event['payload'])) > 500:
                        print(f"  Payload: {str(event['payload'])[:500]}...")
                    else:
                        print(f"  Payload: {event['payload']}")
                print()
            
            # Save decoded version
            output_file = bf.with_suffix('.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(events, f, indent=2)
            print(f"Saved decoded events to: {output_file.name}\n")
            
        except Exception as e:
            print(f"Error decoding: {e}\n")

if __name__ == '__main__':
    main()
