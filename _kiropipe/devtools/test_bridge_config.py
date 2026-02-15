#!/usr/bin/env python3
"""
Test Bridge Server Configuration
Quick test to verify bridge server loads config correctly
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.config_loader import load_config

def test_bridge_config():
    """Test that bridge server can load and use config"""
    print("Testing bridge server configuration...\n")
    
    # Load config
    config = load_config()
    
    if not config:
        print("[ERROR] Failed to load config")
        return False
    
    print("[OK] Config loaded successfully")
    
    # Test model lookup
    print("\nTesting model lookup:")
    test_models = ['kiro-default', 'kiro', 'default']
    
    for model_id in test_models:
        info = config.get_model_info(model_id)
        if info:
            print(f"  ✓ '{model_id}' -> {info['model']['name']} ({info['provider']})")
        else:
            print(f"  ✗ '{model_id}' -> Not found")
            return False
    
    # Test provider config
    print("\nTesting provider config:")
    for provider in config.get_enabled_providers():
        provider_config = config.get_provider_config(provider)
        api_base = config.get_api_base(provider)
        api_key = config.get_api_key(provider)
        
        print(f"  ✓ {provider}:")
        print(f"    Type: {provider_config.get('type')}")
        print(f"    API Base: {api_base if api_base else 'Not set'}")
        print(f"    API Key: {'Configured' if api_key else 'Not set'}")
    
    # Test LiteLLM sub-providers (if enabled)
    litellm_config = config.get_provider_config('litellm')
    if litellm_config and litellm_config.get('enabled'):
        print("\nTesting LiteLLM sub-providers:")
        for sub_provider in ['ollama', 'groq', 'openai', 'openrouter']:
            if sub_provider in litellm_config:
                api_base = config.get_api_base('litellm', sub_provider)
                api_key = config.get_api_key('litellm', sub_provider)
                print(f"  ✓ {sub_provider}:")
                print(f"    API Base: {api_base}")
                print(f"    API Key: {'Configured' if api_key else 'Not set'}")
    
    print("\n[OK] All tests passed!")
    return True


if __name__ == '__main__':
    success = test_bridge_config()
    sys.exit(0 if success else 1)
