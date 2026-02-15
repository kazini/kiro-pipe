#!/usr/bin/env python3
"""
Interactive Configuration Setup
Helps users create kiropipe_config.json
"""

import json
import sys
from pathlib import Path

def main():
    print("="*60)
    print("KiroPipe Configuration Setup")
    print("="*60)
    print()
    
    config_file = Path(__file__).parent.parent / 'kiropipe_config.json'
    example_file = Path(__file__).parent.parent / 'kiropipe_config.json.example'
    
    # Check if config already exists
    if config_file.exists():
        print(f"⚠ Config file already exists: {config_file}")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
        print()
    
    print("Choose your LLM backend:")
    print()
    print("1. Ollama (FREE, local, no API key)")
    print("   - Runs on your computer")
    print("   - Completely private")
    print("   - Requires: ollama installed + model pulled")
    print()
    print("2. Groq (FREE, cloud, API key required)")
    print("   - 14,400 requests/day free")
    print("   - Very fast")
    print("   - Get key at: https://groq.com")
    print()
    print("3. Anthropic Claude (PAID, cloud)")
    print("   - Best quality")
    print("   - Requires paid API key")
    print()
    print("4. OpenAI GPT (PAID, cloud)")
    print("   - Good quality")
    print("   - Requires paid API key")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    print()
    
    config = None
    
    if choice == '1':
        # Ollama
        print("Ollama Configuration")
        print("-" * 60)
        
        # Check if ollama is installed
        try:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✓ Ollama is installed")
                print("\nAvailable models:")
                print(result.stdout)
            else:
                print("⚠ Ollama not found. Install from: https://ollama.ai/download")
        except:
            print("⚠ Ollama not found. Install from: https://ollama.ai/download")
        
        print()
        model = input("Model name (default: llama3.2): ").strip() or "llama3.2"
        api_base = input("API base (default: http://localhost:11434): ").strip() or "http://localhost:11434"
        
        config = {
            "bridge": {
                "backend": "litellm",
                "model": f"ollama/{model}",
                "api_key": None,
                "max_tokens": 4096,
                "debug": True
            },
            "litellm": {
                "enabled": True,
                "model": f"ollama/{model}",
                "api_base": api_base,
                "api_key": None
            }
        }
        
        print()
        print("✓ Configuration created for Ollama")
        print(f"  Model: {model}")
        print(f"  API base: {api_base}")
        print()
        print("Next steps:")
        print(f"  1. Pull model: ollama pull {model}")
        print("  2. Start bridge: python _kiropipe/engine/bridge_server.py")
        print("  3. Test: python _kiropipe/tools/test_ollama_bridge.py")
    
    elif choice == '2':
        # Groq
        print("Groq Configuration")
        print("-" * 60)
        print("Get free API key at: https://groq.com")
        print()
        
        api_key = input("Enter Groq API key: ").strip()
        if not api_key:
            print("✗ API key required")
            return
        
        model = input("Model (default: llama-3.1-70b-versatile): ").strip() or "llama-3.1-70b-versatile"
        
        config = {
            "bridge": {
                "backend": "litellm",
                "model": f"groq/{model}",
                "api_key": None,
                "max_tokens": 4096,
                "debug": True
            },
            "litellm": {
                "enabled": True,
                "model": f"groq/{model}",
                "api_base": None,
                "api_key": api_key
            }
        }
        
        print()
        print("✓ Configuration created for Groq")
        print(f"  Model: {model}")
        print()
        print("Next steps:")
        print("  1. Start bridge: python _kiropipe/engine/bridge_server.py")
        print("  2. Enable bridge in kiropipe.py (ENABLE_BRIDGE = True)")
        print("  3. Run: python kiropipe.py")
    
    elif choice == '3':
        # Anthropic
        print("Anthropic Configuration")
        print("-" * 60)
        print("Requires paid API key from: https://console.anthropic.com")
        print()
        
        api_key = input("Enter Anthropic API key: ").strip()
        if not api_key:
            print("✗ API key required")
            return
        
        model = input("Model (default: claude-3-5-sonnet-20241022): ").strip() or "claude-3-5-sonnet-20241022"
        
        config = {
            "bridge": {
                "backend": "anthropic",
                "model": model,
                "api_key": api_key,
                "max_tokens": 4096,
                "debug": True
            },
            "litellm": {
                "enabled": False
            }
        }
        
        print()
        print("✓ Configuration created for Anthropic")
        print(f"  Model: {model}")
        print()
        print("Next steps:")
        print("  1. Start bridge: python _kiropipe/engine/bridge_server.py")
        print("  2. Enable bridge in kiropipe.py (ENABLE_BRIDGE = True)")
        print("  3. Run: python kiropipe.py")
    
    elif choice == '4':
        # OpenAI
        print("OpenAI Configuration")
        print("-" * 60)
        print("Requires paid API key from: https://platform.openai.com")
        print()
        
        api_key = input("Enter OpenAI API key: ").strip()
        if not api_key:
            print("✗ API key required")
            return
        
        model = input("Model (default: gpt-4): ").strip() or "gpt-4"
        
        config = {
            "bridge": {
                "backend": "openai",
                "model": model,
                "api_key": api_key,
                "max_tokens": 4096,
                "debug": True
            },
            "litellm": {
                "enabled": False
            }
        }
        
        print()
        print("✓ Configuration created for OpenAI")
        print(f"  Model: {model}")
        print()
        print("Next steps:")
        print("  1. Start bridge: python _kiropipe/engine/bridge_server.py")
        print("  2. Enable bridge in kiropipe.py (ENABLE_BRIDGE = True)")
        print("  3. Run: python kiropipe.py")
    
    else:
        print("✗ Invalid choice")
        return
    
    # Save config
    if config:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print()
        print(f"✓ Configuration saved to: {config_file}")
        print()
        print("="*60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
