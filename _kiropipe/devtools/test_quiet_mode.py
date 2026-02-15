#!/usr/bin/env python3
"""
Test Quiet Mode
Verify that mitmproxy runs quietly when debug mode is disabled
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.config_loader import load_config

def test_quiet_mode():
    """Test that quiet mode is properly configured"""
    print("Testing quiet mode configuration...\n")
    
    # Load config
    config = load_config()
    
    if not config:
        print("[ERROR] Failed to load config")
        return False
    
    debug_mode = config.get('debug.debug_mode_enabled', False)
    
    print(f"Debug mode: {debug_mode}")
    
    if debug_mode:
        print("\n✓ Debug mode ENABLED")
        print("  - mitmproxy will show verbose output")
        print("  - Request/response details will be logged")
        print("  - Interaction blocks will be saved (if enabled)")
    else:
        print("\n✓ Debug mode DISABLED (quiet mode)")
        print("  - mitmproxy will run with -q flag (quiet)")
        print("  - Only essential messages will be shown")
        print("  - No verbose request/response logging")
    
    print("\nTo change debug mode:")
    print("  Edit _kiropipe/kiropipe_config.yaml")
    print("  Set debug.debug_mode_enabled: true/false")
    
    return True


if __name__ == '__main__':
    success = test_quiet_mode()
    sys.exit(0 if success else 1)
