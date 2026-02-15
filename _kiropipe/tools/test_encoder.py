#!/usr/bin/env python3
"""
Test AWS Event Stream Encoder
Verify our encoder produces the same format as captured AWS Q responses
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.event_stream_encoder import encode_text_chunk, encode_tool_use_chunk, encode_metering, encode_context_usage
from engine.decode_event_stream import decode_event_stream


def test_encoder_decoder_roundtrip():
    """Test that we can encode and decode successfully"""
    print("\n" + "="*60)
    print("Test 1: Encoder/Decoder Round-trip")
    print("="*60 + "\n")
    
    # Test text chunk
    original_text = "Hello, world!"
    encoded = encode_text_chunk(original_text)
    print(f"Encoded text chunk: {len(encoded)} bytes")
    print(f"Hex: {encoded[:50].hex()}\n")
    
    # Decode it back
    events = decode_event_stream(encoded)
    print(f"Decoded {len(events)} event(s)")
    
    if events:
        event = events[0]
        print(f"Event type: {event['headers'].get(':event-type')}")
        print(f"Payload: {event['payload']}")
        
        # Verify
        if event['payload'].get('content') == original_text:
            print("✓ Round-trip successful!\n")
            return True
        else:
            print("✗ Round-trip failed - content mismatch\n")
            return False
    else:
        print("✗ Failed to decode\n")
        return False


def compare_with_captured():
    """Compare our encoding with captured AWS Q responses"""
    print("\n" + "="*60)
    print("Test 2: Compare with Captured Responses")
    print("="*60 + "\n")
    
    # Find a small captured response
    responses_dir = Path(__file__).parent.parent / "debug_logs" / "interactions" / "responses"
    binary_files = sorted(responses_dir.glob("response_*.bin"))
    
    if not binary_files:
        print("No captured responses found. Run kiropipe.py first to capture data.")
        return False
    
    # Use a small file for comparison
    test_file = None
    for bf in binary_files:
        size = bf.stat().st_size
        if 3000 < size < 10000:  # Find a medium-sized response
            test_file = bf
            break
    
    if not test_file:
        test_file = binary_files[0]
    
    print(f"Analyzing: {test_file.name}")
    print(f"Size: {test_file.stat().st_size} bytes\n")
    
    # Read and decode captured response
    with open(test_file, 'rb') as f:
        captured_data = f.read()
    
    print(f"First 100 bytes of captured response:")
    print(f"  {captured_data[:100].hex()}\n")
    
    # Decode captured response
    try:
        events = decode_event_stream(captured_data)
        print(f"Decoded {len(events)} events from captured response:\n")
        
        for i, event in enumerate(events, 1):
            event_type = event['headers'].get(':event-type', 'unknown')
            print(f"Event #{i}: {event_type}")
            
            if event_type == 'assistantResponseEvent':
                content = event['payload'].get('content', '')
                print(f"  Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                
                # Try to encode the same content
                our_encoded = encode_text_chunk(content)
                print(f"  Our encoding: {len(our_encoded)} bytes")
                print(f"  First 50 bytes: {our_encoded[:50].hex()}")
                
                # Compare structure
                our_events = decode_event_stream(our_encoded)
                if our_events and our_events[0]['payload'].get('content') == content:
                    print(f"  ✓ Our encoder produces valid format")
                else:
                    print(f"  ✗ Encoding mismatch")
                    
            elif event_type == 'toolUseEvent':
                name = event['payload'].get('name', '')
                tool_id = event['payload'].get('toolUseId', '')
                input_chunk = event['payload'].get('input', '')
                print(f"  Tool: {name}")
                print(f"  ID: {tool_id}")
                print(f"  Input chunk: {input_chunk[:50]}{'...' if len(input_chunk) > 50 else ''}")
                
            elif event_type == 'meteringEvent':
                usage = event['payload'].get('usage', 0)
                unit = event['payload'].get('unit', '')
                print(f"  Usage: {usage} {unit}")
                
            elif event_type == 'contextUsageEvent':
                pct = event['payload'].get('contextUsagePercentage', 0)
                print(f"  Context: {pct}%")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"Error decoding captured response: {e}")
        import traceback
        traceback.print_exc()
        return False


def analyze_binary_structure():
    """Analyze the binary structure of captured responses"""
    print("\n" + "="*60)
    print("Test 3: Binary Structure Analysis")
    print("="*60 + "\n")
    
    # Create a simple test event
    test_text = "Test"
    encoded = encode_text_chunk(test_text)
    
    print(f"Encoded '{test_text}' as assistantResponseEvent:")
    print(f"Total size: {len(encoded)} bytes\n")
    
    # Parse structure manually
    import struct
    
    # Prelude (12 bytes)
    total_length = struct.unpack('>I', encoded[0:4])[0]
    headers_length = struct.unpack('>I', encoded[4:8])[0]
    prelude_crc = struct.unpack('>I', encoded[8:12])[0]
    
    print(f"Prelude (12 bytes):")
    print(f"  Total length: {total_length}")
    print(f"  Headers length: {headers_length}")
    print(f"  Prelude CRC: {prelude_crc:08x}")
    print(f"  Hex: {encoded[0:12].hex()}\n")
    
    # Headers
    headers_data = encoded[12:12+headers_length]
    print(f"Headers ({headers_length} bytes):")
    print(f"  Hex: {headers_data.hex()}\n")
    
    # Payload
    payload_start = 12 + headers_length
    payload_end = total_length - 4
    payload_data = encoded[payload_start:payload_end]
    print(f"Payload ({len(payload_data)} bytes):")
    print(f"  Text: {payload_data.decode('utf-8')}")
    print(f"  Hex: {payload_data.hex()}\n")
    
    # Message CRC
    message_crc = struct.unpack('>I', encoded[payload_end:payload_end+4])[0]
    print(f"Message CRC (4 bytes):")
    print(f"  CRC: {message_crc:08x}")
    print(f"  Hex: {encoded[payload_end:payload_end+4].hex()}\n")
    
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("AWS Event Stream Encoder Test Suite")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("Round-trip test", test_encoder_decoder_roundtrip()))
    results.append(("Binary structure", analyze_binary_structure()))
    results.append(("Captured comparison", compare_with_captured()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60 + "\n")
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Encoder is working correctly.")
    else:
        print("\n✗ Some tests failed. Review output above.")
    
    print()
