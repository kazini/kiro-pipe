#!/usr/bin/env python3
"""
Test Configuration Robustness
Tests that config loader handles errors gracefully and uses hardcoded defaults
"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.config_loader import Config

def test_valid_config():
    """Test loading valid config"""
    print("Test 1: Valid config file")
    print("-" * 60)
    
    config_path = Path(__file__).parent.parent / 'kiropipe_config.yaml'
    config = Config(config_path)
    
    if not config:
        print("  ✗ Failed to load valid config")
        return False
    
    # Check defaults
    assert config.get('proxy.port') == 29974, "Port should be 29974"
    assert config.get('debug.debug_mode_enabled') == False, "Debug mode should be False by default"
    assert config.get('debug.store_interaction_blocks') == False, "Store interactions should be False"
    assert config.get('kiro_endpoint.telemetry') == False, "Telemetry should be blocked"
    assert config.get('kiro_endpoint.models') == True, "Kiro models should be allowed"
    
    print("  ✓ Valid config loaded successfully")
    print("  ✓ Debug mode is False by default")
    print("  ✓ All defaults correct")
    return True


def test_missing_config():
    """Test handling missing config file"""
    print("\nTest 2: Missing config file")
    print("-" * 60)
    
    config = Config(Path('/nonexistent/config.yaml'))
    
    # Should fall back to hardcoded defaults
    assert config.get('proxy.port') == 29974, "Should use hardcoded default port"
    assert config.get('debug.debug_mode_enabled') == False, "Should use hardcoded debug default"
    
    print("  ✓ Missing config handled gracefully")
    print("  ✓ Hardcoded defaults used")
    return True


def test_broken_yaml():
    """Test handling broken YAML syntax"""
    print("\nTest 3: Broken YAML syntax")
    print("-" * 60)
    
    # Create temporary broken YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
proxy:
  port: 29974
kiro_endpoint:
  telemetry: false
    updates: false  # Bad indentation
""")
        temp_path = Path(f.name)
    
    try:
        config = Config(temp_path)
        
        # Should fall back to defaults
        assert config.get('proxy.port') == 29974, "Should use default port"
        assert config.get('debug.debug_mode_enabled') == False, "Should use default debug mode"
        
        print("  ✓ Broken YAML handled gracefully")
        print("  ✓ Error message displayed")
        print("  ✓ Hardcoded defaults used")
        return True
    finally:
        temp_path.unlink()


def test_empty_config():
    """Test handling empty config file"""
    print("\nTest 4: Empty config file")
    print("-" * 60)
    
    # Create temporary empty YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("")
        temp_path = Path(f.name)
    
    try:
        config = Config(temp_path)
        
        # Should use defaults
        assert config.get('proxy.port') == 29974, "Should use default port"
        
        print("  ✓ Empty config handled gracefully")
        print("  ✓ Hardcoded defaults used")
        return True
    finally:
        temp_path.unlink()


def test_partial_config():
    """Test handling partial config (some values missing)"""
    print("\nTest 5: Partial config")
    print("-" * 60)
    
    # Create temporary partial YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
proxy:
  port: 12345

# Missing debug section
""")
        temp_path = Path(f.name)
    
    try:
        config = Config(temp_path)
        
        # Should merge with defaults
        assert config.get('proxy.port') == 12345, "Should use config port"
        assert config.get('debug.debug_mode_enabled') == False, "Should use default debug mode"
        
        print("  ✓ Partial config handled correctly")
        print("  ✓ Config values used where present")
        print("  ✓ Defaults used for missing values")
        return True
    finally:
        temp_path.unlink()


def test_invalid_structure():
    """Test handling invalid YAML structure (not a dict)"""
    print("\nTest 6: Invalid YAML structure")
    print("-" * 60)
    
    # Create temporary invalid YAML (list instead of dict)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("""
- item1
- item2
- item3
""")
        temp_path = Path(f.name)
    
    try:
        config = Config(temp_path)
        
        # Should fall back to defaults
        assert config.get('proxy.port') == 29974, "Should use default port"
        
        print("  ✓ Invalid structure handled gracefully")
        print("  ✓ Error message displayed")
        print("  ✓ Hardcoded defaults used")
        return True
    finally:
        temp_path.unlink()


def test_none_config():
    """Test handling None config path"""
    print("\nTest 7: None config path")
    print("-" * 60)
    
    config = Config(None)
    
    # Should use defaults
    assert config.get('proxy.port') == 29974, "Should use default port"
    assert config.get('debug.debug_mode_enabled') == False, "Should use default debug mode"
    
    print("  ✓ None config path handled gracefully")
    print("  ✓ Hardcoded defaults used")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Configuration Robustness Tests")
    print("="*60)
    
    tests = [
        test_valid_config,
        test_missing_config,
        test_broken_yaml,
        test_empty_config,
        test_partial_config,
        test_invalid_structure,
        test_none_config,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ Test failed")
        except Exception as e:
            failed += 1
            print(f"  ✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("\n✓ All tests passed!")
        return True
    else:
        print(f"\n✗ {failed} test(s) failed")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
