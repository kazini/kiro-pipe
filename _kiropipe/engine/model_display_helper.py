#!/usr/bin/env python3
"""
Model Display Helper
Determines how to display model cost/quota information
"""

from typing import Dict, Any, Optional, Tuple


def get_model_display_info(
    model_id: str,
    model_name: str,
    description: str,
    cost_info: Optional[Dict[str, Any]],
    quota_manager: Any,
    quota_enabled: bool
) -> Tuple[Optional[float], str, str]:
    """
    Determine display information for a model
    
    Args:
        model_id: Model identifier
        model_name: Display name
        description: Base description
        cost_info: Cost information from get_model_cost()
        quota_manager: QuotaManager instance
        quota_enabled: Whether quota tracking is enabled
    
    Returns:
        Tuple of (rateMultiplier, rateUnit, description)
    
    Display Priority:
    1. Quota percentage (if API provides headers) → "45% Quota"
    2. FREE (if model is free with quota limits but no overage) → "FREE"
    3. Cost (if model has overage charges) → "0.69 $/1M Token"
    4. Unknown → "UNKNOWN"
    """
    # Check if we have quota data
    quota_percentage = None
    if quota_enabled and quota_manager:
        quota_percentage = quota_manager.get_quota_percentage(model_id)
    
    # Priority 1: Show quota if available
    if quota_percentage is not None:
        rate_multiplier = quota_percentage
        rate_unit = "% Quota"
        
        # Add overage cost to description if not free
        if cost_info and not cost_info['is_free']:
            input_per_m = cost_info['input_cost_per_token'] * 1_000_000
            output_per_m = cost_info['output_cost_per_token'] * 1_000_000
            avg_per_m = (input_per_m + output_per_m) / 2
            overage_detail = f"  |  [{avg_per_m:.2f} $/1M Overage]"
            description = description + overage_detail
        
        return (rate_multiplier, rate_unit, description)
    
    # Priority 2: Show FREE if model is free (even if it has quota limits)
    # This applies to models like Groq where there's a quota but no overage charges
    if cost_info and cost_info['is_free']:
        rate_multiplier = None
        rate_unit = "FREE"
        return (rate_multiplier, rate_unit, description)
    
    # Priority 3: Show cost if model has overage charges
    if cost_info and not cost_info['is_free']:
        # Convert to cost per 1M tokens
        input_per_m = cost_info['input_cost_per_token'] * 1_000_000
        output_per_m = cost_info['output_cost_per_token'] * 1_000_000
        avg_per_m = (input_per_m + output_per_m) / 2
        
        rate_multiplier = round(avg_per_m, 2)
        rate_unit = "$/1M Token"
        
        return (rate_multiplier, rate_unit, description)
    
    # Priority 4: Unknown cost
    return (None, "UNKNOWN", description)


def should_create_overage_variant(
    model_id: str,
    quota_manager: Any,
    quota_settings: Dict[str, Any]
) -> bool:
    """
    Check if we should create an overage variant
    
    Args:
        model_id: Model identifier
        quota_manager: QuotaManager instance
        quota_settings: Quota settings from config
    
    Returns:
        True if overage variant should be created
    """
    if not quota_manager:
        return False
    
    block_threshold = quota_settings.get('block_at_percent', 100)
    return quota_manager.is_quota_exhausted(model_id, block_threshold)


def get_overage_model_name(base_name: str) -> str:
    """
    Get overage variant model name
    
    Args:
        base_name: Base model name or alias
    
    Returns:
        Overage variant name (e.g., "Llama 3.3 70B-Overage")
    """
    return f"{base_name}-Overage"
