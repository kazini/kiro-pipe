#!/usr/bin/env python3
"""
Configuration Loader
Loads and validates YAML configuration with fallbacks to hardcoded defaults
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)


# ============================================================
# HARDCODED DEFAULTS (used if config file missing)
# ============================================================
DEFAULT_CONFIG = {
    'proxy': {
        'port': 29974
    },
    'kiro': {
        'exe_path': None
    },
    'kiro_endpoint': {
        'telemetry': False,  # FALSE = block
        'updates': False,    # FALSE = block
        'models': True,      # TRUE = allow
        'force_toggle_usage_limits': None
    },
    'debug': {
        'debug_mode_enabled': False,
        'store_interaction_blocks': False
    },
    'providers': {
        'kiro': {
            'enabled': True,
            'type': 'passthrough',
            'description': "Kiro's default AWS Q models",
            'models': [
                {
                    'name': 'kiro-default',
                    'alias': ['kiro', 'default', 'aws-q'],
                    'description': "Kiro's default model"
                }
            ]
        }
    },
    'default_model': 'kiro-default'
}


class Config:
    """Configuration manager with fallbacks"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path
        # Always start with defaults
        self.config = self._deep_copy(DEFAULT_CONFIG)
        self.model_map = {}  # name/alias -> provider, model
        
        if config_path and config_path.exists():
            self.load_from_file(config_path)
        elif config_path:
            print(f"[Config] Config file not found: {config_path}")
            print(f"[Config] Using defaults")
        else:
            print(f"[Config] No config file found, using defaults")
        
        self.build_model_map()
    
    def _deep_copy(self, obj):
        """Deep copy a dictionary"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    def load_from_file(self, config_path: Path):
        """Load configuration from YAML file with robust error handling"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            
            if not file_config:
                print(f"[Config] Empty config file, using defaults")
                return
            
            # Validate YAML structure
            if not isinstance(file_config, dict):
                print(f"[Config] ERROR: Config file must contain a YAML dictionary")
                print(f"[Config] Using defaults")
                return
            
            # Deep merge with defaults
            self._deep_merge(self.config, file_config)
            print(f"[Config] Loaded from {config_path}")
            
        except yaml.YAMLError as e:
            print(f"[Config] ERROR: Invalid YAML syntax in {config_path}")
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                print(f"[Config]   Line {mark.line + 1}, Column {mark.column + 1}")
            if hasattr(e, 'problem'):
                print(f"[Config]   {e.problem}")
            if hasattr(e, 'context'):
                print(f"[Config]   {e.context}")
            print(f"[Config] Using defaults")
            print(f"\n[Config] TIP: Validate your YAML at https://www.yamllint.com/")
        except FileNotFoundError:
            print(f"[Config] Config file not found: {config_path}")
            print(f"[Config] Using defaults")
        except PermissionError:
            print(f"[Config] ERROR: Permission denied reading {config_path}")
            print(f"[Config] Using defaults")
        except Exception as e:
            print(f"[Config] ERROR: Failed to load config: {e}")
            print(f"[Config] Using defaults")
    
    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override into base"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def build_model_map(self):
        """Build map of model names/aliases to providers"""
        self.model_map = {}
        
        for provider_name, provider_config in self.config.get('providers', {}).items():
            if not provider_config.get('enabled', False):
                continue
            
            models = provider_config.get('models', [])
            for model in models:
                model_name = model.get('name')
                if not model_name:
                    continue
                
                # Add model name
                self.model_map[model_name] = {
                    'provider': provider_name,
                    'model': model
                }
                
                # Add aliases
                aliases = model.get('alias', [])
                for alias in aliases:
                    self.model_map[alias] = {
                        'provider': provider_name,
                        'model': model
                    }
    
    def get_model_info(self, model_identifier: str) -> Optional[Dict[str, Any]]:
        """Get model info by name or alias"""
        return self.model_map.get(model_identifier)
    
    def get_default_model(self) -> str:
        """Get default model identifier"""
        return self.config.get('default_model', 'kiro-default')
    
    def get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get provider configuration"""
        return self.config.get('providers', {}).get(provider_name)
    
    def get_api_base(self, provider_name: str, sub_provider: Optional[str] = None) -> Optional[str]:
        """
        Get api_base for a provider or sub-provider
        
        Args:
            provider_name: Main provider (e.g., 'anthropic', 'litellm')
            sub_provider: Sub-provider for litellm (e.g., 'ollama', 'groq', 'openai')
        
        Returns:
            api_base URL or None
        """
        provider_config = self.get_provider_config(provider_name)
        if not provider_config:
            return None
        
        # For litellm, check sub-provider first
        if provider_name == 'litellm' and sub_provider:
            sub_config = provider_config.get(sub_provider, {})
            return sub_config.get('api_base')
        
        # For direct providers (anthropic, etc.)
        return provider_config.get('api_base')
    
    def get_api_key(self, provider_name: str, sub_provider: Optional[str] = None) -> Optional[str]:
        """
        Get api_key for a provider or sub-provider
        
        Args:
            provider_name: Main provider (e.g., 'anthropic', 'litellm')
            sub_provider: Sub-provider for litellm (e.g., 'ollama', 'groq', 'openai')
        
        Returns:
            api_key or None
        """
        provider_config = self.get_provider_config(provider_name)
        if not provider_config:
            return None
        
        # For litellm, check sub-provider first
        if provider_name == 'litellm' and sub_provider:
            sub_config = provider_config.get(sub_provider, {})
            return sub_config.get('api_key')
        
        # For direct providers (anthropic, etc.)
        return provider_config.get('api_key')
    
    def is_kiro_model(self, model_identifier: str) -> bool:
        """Check if model is a Kiro passthrough model"""
        info = self.get_model_info(model_identifier)
        if not info:
            return False
        
        provider = self.get_provider_config(info['provider'])
        return provider and provider.get('type') == 'passthrough'
    
    def should_block_usage_limits(self, current_model: Optional[str] = None) -> bool:
        """
        Determine if usage limits should be blocked
        
        Logic:
        - force_toggle_usage_limits = None: Auto (allow for Kiro models, block otherwise)
        - force_toggle_usage_limits = True: Always allow
        - force_toggle_usage_limits = False: Always block
        """
        force = self.config.get('kiro_endpoint', {}).get('force_toggle_usage_limits')
        
        if force is True:
            return False  # Always allow (don't block)
        elif force is False:
            return True  # Always block
        else:
            # Auto mode: allow for Kiro models, block for custom
            if current_model and self.is_kiro_model(current_model):
                return False  # Allow for Kiro models
            else:
                return True  # Block for custom models
    
    def should_allow_request(self, request_path: str, current_model: Optional[str] = None) -> bool:
        """
        Determine if a request should be allowed through
        
        Returns False if ALL of these are blocked (FALSE):
        - Telemetry
        - Updates
        - Usage limits
        - Kiro models
        """
        kiro_endpoint = self.config.get('kiro_endpoint', {})
        
        # If all endpoints are blocked (FALSE) and Kiro models are blocked, nothing gets through
        if (not kiro_endpoint.get('telemetry', False) and 
            not kiro_endpoint.get('updates', False) and
            not kiro_endpoint.get('models', True) and
            self.should_block_usage_limits(current_model)):
            return False
        
        return True
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider names"""
        providers = []
        for name, config in self.config.get('providers', {}).items():
            if config.get('enabled', False):
                providers.append(name)
        return providers
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """Get all models from all enabled providers"""
        models = []
        for provider_name, provider_config in self.config.get('providers', {}).items():
            if not provider_config.get('enabled', False):
                continue
            
            for model in provider_config.get('models', []):
                models.append({
                    'provider': provider_name,
                    'name': model.get('name'),
                    'aliases': model.get('alias', []),
                    'description': model.get('description', ''),
                    'max_tokens': model.get('max_tokens', 4096)
                })
        
        return models
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get config value by dot-separated path
        Example: config.get('blocking.telemetry')
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def print_summary(self):
        """Print configuration summary"""
        print("\n" + "="*60)
        print("Configuration Summary")
        print("="*60)
        
        print(f"\nProxy:")
        print(f"  Port: {self.get('proxy.port')}")
        
        print(f"\nKiro:")
        exe_path = self.get('kiro.exe_path')
        print(f"  Exe path: {exe_path if exe_path else 'Auto-detect'}")
        
        print(f"\nKiro Endpoint (TRUE=allow, FALSE=block):")
        print(f"  Telemetry: {self.get('kiro_endpoint.telemetry')}")
        print(f"  Updates: {self.get('kiro_endpoint.updates')}")
        print(f"  Models: {self.get('kiro_endpoint.models')}")
        print(f"  Force toggle usage limits: {self.get('kiro_endpoint.force_toggle_usage_limits')}")
        
        print(f"\nDebug:")
        print(f"  Debug mode enabled: {self.get('debug.debug_mode_enabled')}")
        print(f"  Store interaction blocks: {self.get('debug.store_interaction_blocks')}")
        
        print(f"\nEnabled Providers:")
        for provider in self.get_enabled_providers():
            provider_config = self.get_provider_config(provider)
            print(f"  - {provider}: {provider_config.get('description', '')}")
        
        print(f"\nAvailable Models:")
        for model in self.get_all_models():
            aliases = ', '.join(model['aliases']) if model['aliases'] else 'none'
            print(f"  - {model['name']} ({model['provider']})")
            print(f"    Aliases: {aliases}")
            print(f"    {model['description']}")
        
        print(f"\nDefault Model: {self.get_default_model()}")
        
        print("="*60 + "\n")


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or use defaults"""
    if config_path is None:
        # Try to find config file
        script_dir = Path(__file__).parent.parent
        yaml_path = script_dir / 'kiropipe_config.yaml'
        
        if yaml_path.exists():
            config_path = yaml_path
    
    return Config(config_path)


# Test function
if __name__ == '__main__':
    print("Testing configuration loader...\n")
    
    # Load config
    config = load_config()
    
    # Print summary
    config.print_summary()
    
    # Test model lookup
    print("\nTesting model lookup:")
    test_identifiers = ['kiro-default', 'kiro', 'default', 'claude', 'nonexistent']
    
    for identifier in test_identifiers:
        info = config.get_model_info(identifier)
        if info:
            print(f"  '{identifier}' -> {info['model']['name']} ({info['provider']})")
        else:
            print(f"  '{identifier}' -> Not found")
    
    # Test usage limits logic
    print("\nTesting usage limits logic:")
    print(f"  Default model: {config.should_block_usage_limits()}")
    print(f"  Kiro model: {config.should_block_usage_limits('kiro-default')}")
    print(f"  Custom model: {config.should_block_usage_limits('claude')}")
    
    print("\n[OK] Configuration loader test complete!")
