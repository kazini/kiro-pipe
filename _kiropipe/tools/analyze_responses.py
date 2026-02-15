#!/usr/bin/env python3
"""
Analyze captured responses and compare with known plaintext
"""

import json
import sys
from pathlib import Path

def analyze_captured_data():
    """Analyze captured requests and responses"""
    
    print("\n" + "="*60)
    print("Captured Data Analysis")
    print("="*60 + "\n")
    
    # Check for captured files
    requests_file = Path('captured_requests.jsonl')
    responses_file = Path('captured_responses.jsonl')
    
    if not requests_file.exists() and not responses_file.exists():
        print("No captured data found.")
        print("Run the proxy and use Kiro's AI features first.")
        return
    
    # Analyze requests
    if requests_file.exists():
        print("REQUESTS:")
        print("-" * 60)
        with open(requests_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                try:
                    data = json.loads(line)
                    print(f"\nRequest #{i}:")
                    print(f"  URL: {data['url']}")
                    
                    # Parse body if it's JSON string
                    if isinstance(data['body'], str):
                        try:
                            body = json.loads(data['body'])
                            # Extract user message
                            user_msg = body.get('conversationState', {}).get('currentMessage', {}).get('userInputMessage', {}).get('content', '')
                            if user_msg:
                                print(f"  User Message: {user_msg[:100]}...")
                        except:
                            pass
                except Exception as e:
                    print(f"  Error parsing request {i}: {e}")
        print()
    
    # Analyze responses
    if responses_file.exists():
        print("\nRESPONSES:")
        print("-" * 60)
        with open(responses_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                try:
                    data = json.loads(line)
                    print(f"\nResponse #{i}:")
                    print(f"  URL: {data['url']}")
                    print(f"  Status: {data['status']}")
                    print(f"  Content-Type: {data['headers'].get('content-type', 'unknown')}")
                    
                    # Show body preview
                    body = data['body']
                    if isinstance(body, dict):
                        print(f"  Format: JSON")
                        print(f"  Keys: {list(body.keys())}")
                        # Try to find the AI response text
                        body_str = json.dumps(body, indent=2)
                        if len(body_str) > 500:
                            print(f"  Preview:\n{body_str[:500]}...")
                        else:
                            print(f"  Body:\n{body_str}")
                    elif isinstance(body, str):
                        print(f"  Format: Text/String")
                        if len(body) > 200:
                            print(f"  Preview: {body[:200]}...")
                        else:
                            print(f"  Body: {body}")
                    else:
                        print(f"  Format: {type(body)}")
                except Exception as e:
                    print(f"  Error parsing response {i}: {e}")
        print()
    
    # Check for binary files
    binary_files = list(Path('.').glob('response_binary_*.bin'))
    if binary_files:
        print("\nBINARY RESPONSES:")
        print("-" * 60)
        for bf in binary_files:
            print(f"\n{bf.name}:")
            with open(bf, 'rb') as f:
                data = f.read()
                print(f"  Size: {len(data)} bytes")
                print(f"  First 50 bytes (hex): {data[:50].hex()}")
                
                # Try to identify format
                if data[:2] == b'\x1f\x8b':
                    print(f"  Format: GZIP compressed")
                elif data[:2] == b'PK':
                    print(f"  Format: ZIP archive")
                elif data[:4] == b'\x00\x00\x00':
                    print(f"  Format: Possibly protobuf")
                else:
                    print(f"  Format: Unknown binary")
    
    print("\n" + "="*60)
    print("\nTo compare with Kiro UI:")
    print("1. Note the AI's response text in Kiro")
    print("2. Find the corresponding response above")
    print("3. Compare to identify the encoding")
    print("="*60 + "\n")

if __name__ == '__main__':
    analyze_captured_data()
