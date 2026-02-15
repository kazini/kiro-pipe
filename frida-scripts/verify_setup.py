#!/usr/bin/env python3
"""
Quick verification script to check if spawn gating is ready to test
"""

import sys
from pathlib import Path

def check_file(path, description):
    """Check if a file exists"""
    if Path(path).exists():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description} MISSING: {path}")
        return False

def main():
    print("\n" + "="*60)
    print("Frida Spawn Gating Setup Verification")
    print("="*60 + "\n")
    
    all_good = True
    
    # Check Python script
    all_good &= check_file("attach.py", "Main script")
    
    # Check hook files
    print("\nHook files:")
    all_good &= check_file("kiro_api_hook.js", "  AWS Q hook")
    check_file("test_any_network.js", "  Network test hook")
    check_file("chromium_network_hook.js", "  Chromium hook")
    
    # Check batch file
    print("\nTest scripts:")
    all_good &= check_file("test_spawn.bat", "  Windows batch")
    
    # Check documentation
    print("\nDocumentation:")
    check_file("SPAWN_TESTING.md", "  Testing guide")
    check_file("KIRO_NETWORK_INTERCEPTION_GUIDE.md", "  Main guide")
    
    # Check Frida
    print("\nDependencies:")
    try:
        import frida
        print(f"✓ Frida installed: v{frida.__version__}")
    except ImportError:
        print("✗ Frida NOT installed")
        print("  Install with: pip install frida")
        all_good = False
    
    # Summary
    print("\n" + "="*60)
    if all_good:
        print("✓ ALL CHECKS PASSED - READY FOR TESTING")
        print("\nRun one of these commands:")
        print("  1. test_spawn.bat")
        print("  2. python attach.py --spawn --hook kiro_api_hook")
    else:
        print("✗ SOME CHECKS FAILED - FIX ISSUES ABOVE")
    print("="*60 + "\n")
    
    return 0 if all_good else 1

if __name__ == '__main__':
    sys.exit(main())
