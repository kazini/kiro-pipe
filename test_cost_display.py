#!/usr/bin/env python3
"""Test cost display for Groq models"""
import sys
sys.path.insert(0, '_kiropipe')

from engine.litellm_handler import get_model_cost
from engine.model_display_helper import get_model_display_info
from engine.quota_manager import get_quota_manager

# Test Groq models
models = [
    ('groq/llama-3.3-70b-versatile', 'Groq Llama Flex 3.3 70B', 'Flexible and capable.'),
    ('groq/llama-3.1-8b-instant', 'Groq Llama Lite 3.1 8B', 'Fast and with large capacity.')
]

quota_manager = get_quota_manager()
quota_enabled = True

print("Testing cost display for Groq models:\n")
print("="*60)

for model_id, model_name, description in models:
    print(f"\nModel: {model_id}")
    print(f"Display Name: {model_name}")
    
    # Get cost info
    cost_info = get_model_cost(model_id, 'groq')
    print(f"Cost Info: {cost_info}")
    
    # Get display info
    rate_multiplier, rate_unit, final_description = get_model_display_info(
        model_id, model_name, description,
        cost_info, quota_manager, quota_enabled
    )
    
    print(f"Rate Multiplier: {rate_multiplier}")
    print(f"Rate Unit: {rate_unit}")
    print(f"Description: {final_description}")
    print("-"*60)
