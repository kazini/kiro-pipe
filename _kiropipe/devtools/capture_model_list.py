#!/usr/bin/env python3
"""
Capture Model List Response

Analyzes the most recent ListAvailableModels response to understand the format.
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.decode_event_stream import decode_event_stream


def find_model_list_response():
    """Find the most recent ListAvailableModels response"""
    
    responses_dir = Path(__file__).parent.parent / "debug_logs" / "interactions" / "responses"
    
    if not responses_dir.exists():
        print("No responses directory found. Enable debug mode and store_interaction_blocks.")
        return None
    
    # Look for the most recent response
    response_files = sorted(responses_dir.glob("response_*.bin"), 
                          key=lambda x: x.stat().st_mtime, 
                          reverse=True)
    
    if not response_files:
        print("No response files found.")
        return None
    
    # Check the most recent one (should be ListAvailableModels)
    latest = response_files[0]
    print(f"Analyzing: {latest.name}")
    print(f"Size: {latest.stat().st_size} bytes")
    
    return latest


def analyze_response(response_file: Path):
    """Analyze the response format"""
    
    print("\n" + "="*60)
    print("ANALYZING MODEL LIST RESPONSE")
    print("="*60)
    
    # Read binary
    binary_data = response_file.read_bytes()
    
    # Try to decode as JSON first
    try:
        json_data = json.loads(binary_data.decode('utf-8'))
        print("\n[FORMAT] JSON")
        print(json.dumps(json_data, indent=2))
        return json_data
    except:
        pass
    
    # Try to decode as AWS Event Stream
    try:
        events = decode_event_stream(binary_data)
        print("\n[FORMAT] AWS Event Stream")
        print(f"Events: {len(events)}")
        
        for i, event in enumerate(events):
            print(f"\nEvent {i+1}:")
            print(f"  Type: {event.get('event_type', 'unknown')}")
            print(f"  Payload: {json.dumps(event.get('payload', {}), indent=4)}")
        
        return events
    except Exception as e:
        print(f"\n[ERROR] Could not decode: {e}")
    
    # Show raw hex
    print("\n[FORMAT] Unknown - showing hex:")
    print(binary_data[:200].hex())
    
    return None


def main():
    """Main function"""
    
    print("\n" + "="*60)
    print("MODEL LIST RESPONSE CAPTURE")
    print("="*60)
    
    # Find response
    response_file = find_model_list_response()
    
    if not response_file:
        print("\nNo response file found.")
        print("\nTo capture:")
        print("1. Enable debug mode in kiropipe_config.yaml:")
        print("   debug:")
        print("     debug_mode_enabled: true")
        print("     store_interaction_blocks: true")
        print("\n2. Restart kiropipe.py")
        print("3. Open Kiro and trigger model list (it should happen automatically)")
        print("4. Run this script again")
        return 1
    
    # Analyze
    data = analyze_response(response_file)
    
    if data:
        print("\n" + "="*60)
        print("SUCCESS - Response decoded!")
        print("="*60)
        print("\nNow we can create a fake model list in the same format.")
    else:
        print("\n" + "="*60)
        print("Could not decode response")
        print("="*60)
        print("\nThe response might be in a different format.")
        print("Check the hex output above for clues.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
