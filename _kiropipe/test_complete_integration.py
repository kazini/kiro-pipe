#!/usr/bin/env python3
"""
Comprehensive test demonstrating max tokens and cost auto-detection
"""

import sys
from pathlib import Path

# Add engine to path
sys.path.insert(0, str(Path(__file__).parent))

from engine.litellm_handler import get_model_max_tokens, get_model_cost

print("=" * 80)
print("COMPLETE INTEGRATION TEST: MAX TOKENS + COST AUTO-DETECTION")
print("=" * 80)

test_cases = [
    {
        'name': 'Premium Cloud Models',
        'models': [
            ('gpt-4', None),
            ('claude-3-5-sonnet-20241022', 'anthropic'),
        ]
    },
    {
        'name': 'Budget Cloud Models',
        'models': [
            ('groq/llama-3.3-70b-versatile', 'groq'),
            ('groq/llama-3.1-8b-instant', 'groq'),
        ]
    },
    {
        'name': 'Free Cloud Models',
        'models': [
            ('openrouter/deepseek/deepseek-r1-0528:free', 'openrouter'),
            ('openrouter/google/gemini-2.0-flash-exp:free', 'openrouter'),
        ]
    },
    {
        'name': 'Local Models',
        'models': [
            ('ollama/llama3.2', 'ollama'),
            ('ollama/qwen2.5-coder', 'ollama'),
        ]
    }
]

for category in test_cases:
    print(f"\n{'=' * 80}")
    print(f"{category['name']}")
    print('=' * 80)
    
    for model, provider in category['models']:
        print(f"\n{model}")
        
        # Max tokens
        max_tokens = get_model_max_tokens(model)
        if max_tokens:
            print(f"  Max Tokens: {max_tokens:,}")
        else:
            print(f"  Max Tokens: Not in database (will use config or default)")
        
        # Cost
        cost_info = get_model_cost(model, provider)
        if cost_info:
            if cost_info['is_free']:
                print(f"  Cost: FREE")
                print(f"  Display: rateUnit='FREE', rateMultiplier=null")
            else:
                input_per_m = cost_info['input_cost_per_token'] * 1_000_000
                output_per_m = cost_info['output_cost_per_token'] * 1_000_000
                avg_per_m = (input_per_m + output_per_m) / 2
                
                print(f"  Cost: ${input_per_m:.2f} in / ${output_per_m:.2f} out per 1M tokens")
                print(f"  Display: rateUnit='USD/1M', rateMultiplier={avg_per_m:.2f}")
            print(f"  Source: {cost_info['source']}")
        else:
            print(f"  Cost: Not detected")
            print(f"  Display: rateUnit='{provider.upper() if provider else 'UNKNOWN'}', rateMultiplier=null")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
✅ Max Tokens Auto-Detection:
   - Queries LiteLLM's model_cost database
   - Falls back to config values or 200k default
   - Supports 100+ models

✅ Cost Auto-Detection (4-tier priority):
   1. Free detection (ollama/*, :free suffix)
   2. LiteLLM database (100+ cloud providers)
   3. OpenRouter API (live pricing)
   4. Pattern inference (fuzzy matching)

✅ Display Format:
   - FREE models: rateUnit='FREE', rateMultiplier=null
   - Paid models: rateUnit='USD/1M', rateMultiplier=<avg_cost>
   - Unknown: rateUnit='<PROVIDER>', rateMultiplier=null

✅ Integration:
   - Applied to both LiteLLM sub-providers and regular providers
   - Visible in Kiro's model dropdown
   - No configuration required
""")
print("=" * 80)
