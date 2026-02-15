#!/usr/bin/env python3
"""
Endpoint Discovery Tool

Monitors all AWS Q API calls to discover what endpoints Kiro uses,
particularly for model listing and selection.

Usage:
    1. Enable debug mode in kiropipe_config.yaml
    2. Run kiropipe.py
    3. In Kiro, try to change models or open model selection
    4. Check output for discovered endpoints
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_captured_traffic():
    """Analyze captured traffic to find model-related endpoints"""
    
    debug_dir = Path(__file__).parent.parent / "debug_logs" / "interactions"
    posted_dir = debug_dir / "posted"
    responses_dir = debug_dir / "responses"
    
    if not posted_dir.exists() or not responses_dir.exists():
        print("No captured traffic found.")
        print("Enable debug mode and store_interaction_blocks in config.")
        return
    
    print("="*60)
    print("ENDPOINT DISCOVERY")
    print("="*60)
    
    # Analyze requests
    endpoints = {}
    
    for request_file in sorted(posted_dir.glob("*.json")):
        try:
            import json
            with open(request_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            url = data.get('url', '')
            path = url.split('amazonaws.com')[-1] if 'amazonaws.com' in url else url
            
            if path not in endpoints:
                endpoints[path] = {
                    'count': 0,
                    'methods': set(),
                    'sample_file': request_file.name
                }
            
            endpoints[path]['count'] += 1
            method = data.get('headers', {}).get('method', 'UNKNOWN')
            endpoints[path]['methods'].add(method)
            
        except Exception as e:
            print(f"Error reading {request_file}: {e}")
    
    # Print discovered endpoints
    print(f"\nDiscovered {len(endpoints)} unique endpoints:\n")
    
    for path, info in sorted(endpoints.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"Path: {path}")
        print(f"  Calls: {info['count']}")
        print(f"  Methods: {', '.join(info['methods'])}")
        print(f"  Sample: {info['sample_file']}")
        print()
    
    # Look for model-related endpoints
    print("="*60)
    print("MODEL-RELATED ENDPOINTS")
    print("="*60)
    
    model_keywords = ['model', 'list', 'available', 'select', 'choice', 'option']
    
    found_model_endpoints = False
    for path, info in endpoints.items():
        if any(keyword in path.lower() for keyword in model_keywords):
            print(f"\nFound: {path}")
            print(f"  Calls: {info['count']}")
            print(f"  Sample file: {info['sample_file']}")
            found_model_endpoints = True
    
    if not found_model_endpoints:
        print("\nNo model-related endpoints found yet.")
        print("\nTo discover model endpoints:")
        print("  1. Open Kiro")
        print("  2. Try to change the model selection")
        print("  3. Look at the chat interface for model dropdown")
        print("  4. Run this script again")

if __name__ == '__main__':
    analyze_captured_traffic()
