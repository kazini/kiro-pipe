#!/usr/bin/env python3
"""
Test Model List Injection

This tool tests whether Kiro has a hardcoded or dynamic model list by:
1. Intercepting model-related API calls
2. Injecting fake model lists
3. Observing if Kiro displays the fake models

Strategy:
- Monitor for any API calls that might fetch model lists
- Create fake responses with custom model names
- Test if Kiro accepts and displays them
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.event_stream_encoder import encode_event


def create_fake_model_list_response():
    """
    Create a fake model list response to test if Kiro accepts it
    
    This tests whether Kiro:
    - Has a hardcoded model list (won't show our fake models)
    - Has a dynamic model list (will show our fake models)
    """
    
    # Hypothetical model list structure (we'll test different formats)
    fake_models = [
        {
            "id": "custom-model-1",
            "name": "Custom Test Model 1",
            "description": "A fake model to test dynamic loading",
            "provider": "test",
            "capabilities": ["chat", "tools"]
        },
        {
            "id": "custom-model-2", 
            "name": "Custom Test Model 2",
            "description": "Another fake model",
            "provider": "test",
            "capabilities": ["chat"]
        },
        # Include some real models to see if they get merged
        {
            "id": "claude-3-5-sonnet-20241022",
            "name": "Claude 3.5 Sonnet",
            "description": "Real model (should already exist)",
            "provider": "anthropic",
            "capabilities": ["chat", "tools"]
        }
    ]
    
    return fake_models


def create_model_list_event(models: list) -> bytes:
    """
    Create an AWS Event Stream event with model list
    
    We'll try different event types to see what Kiro expects:
    - modelListEvent
    - availableModelsEvent
    - configurationEvent
    """
    
    # Try different payload structures
    payloads = [
        # Format 1: Simple list
        {"models": models},
        
        # Format 2: With metadata
        {
            "models": models,
            "default": "claude-3-5-sonnet-20241022",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        
        # Format 3: Nested structure
        {
            "configuration": {
                "availableModels": models,
                "defaultModel": "claude-3-5-sonnet-20241022"
            }
        }
    ]
    
    # Try different event types
    event_types = [
        'modelListEvent',
        'availableModelsEvent', 
        'configurationEvent',
        'modelConfigurationEvent'
    ]
    
    print("="*60)
    print("FAKE MODEL LIST GENERATION")
    print("="*60)
    print(f"\nGenerating {len(event_types)} event types x {len(payloads)} payload formats")
    print(f"= {len(event_types) * len(payloads)} test variations\n")
    
    results = []
    
    for event_type in event_types:
        for i, payload in enumerate(payloads):
            try:
                encoded = encode_event(event_type, payload)
                results.append({
                    'event_type': event_type,
                    'payload_format': i + 1,
                    'size': len(encoded),
                    'binary': encoded
                })
                print(f"✓ {event_type} (format {i+1}): {len(encoded)} bytes")
            except Exception as e:
                print(f"✗ {event_type} (format {i+1}): {e}")
    
    print(f"\n✓ Generated {len(results)} test variations")
    
    return results


def save_test_injections(variations: list):
    """Save test variations for manual injection"""
    
    output_dir = Path(__file__).parent.parent / 'debug_logs' / 'model_tests'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print("SAVING TEST FILES")
    print(f"{'='*60}\n")
    
    for i, var in enumerate(variations):
        # Save binary
        bin_file = output_dir / f"test_{i+1}_{var['event_type']}_format{var['payload_format']}.bin"
        bin_file.write_bytes(var['binary'])
        
        # Save metadata
        meta_file = output_dir / f"test_{i+1}_{var['event_type']}_format{var['payload_format']}.json"
        meta_file.write_text(json.dumps({
            'event_type': var['event_type'],
            'payload_format': var['payload_format'],
            'size': var['size']
        }, indent=2))
        
        print(f"✓ Saved: {bin_file.name}")
    
    print(f"\n✓ All test files saved to: {output_dir}")
    
    return output_dir


def create_injection_instructions():
    """Create instructions for testing"""
    
    instructions = """
="*60
MODEL LIST INJECTION TEST - INSTRUCTIONS
="*60

OBJECTIVE:
Test whether Kiro has a hardcoded or dynamic model list.

HYPOTHESIS:
- If Kiro has a HARDCODED list: Our fake models won't appear
- If Kiro has a DYNAMIC list: Our fake models will appear in the UI

TEST PROCEDURE:

1. MONITOR ENDPOINTS
   - Enable debug mode in kiropipe_config.yaml:
     debug:
       debug_mode_enabled: true
       store_interaction_blocks: true
   
   - Run: python kiropipe.py
   
   - In Kiro, look for model selection UI
   - Check console output for any API calls containing:
     * "model"
     * "list"
     * "available"
     * "configuration"

2. IDENTIFY MODEL ENDPOINT
   - Look at captured requests in _kiropipe/debug_logs/interactions/posted/
   - Find any requests that might fetch model lists
   - Note the endpoint path (e.g., /getAvailableModels)

3. INJECT FAKE RESPONSE
   - Once endpoint is identified, modify kiropipe.py to intercept it
   - Add code like:
   
     if 'getAvailableModels' in flow.request.path:
         # Load one of our test binaries
         test_file = Path('_kiropipe/debug_logs/model_tests/test_1_modelListEvent_format1.bin')
         fake_response = test_file.read_bytes()
         
         flow.response = http.Response.make(
             200,
             fake_response,
             {"Content-Type": "application/vnd.amazon.eventstream"}
         )
         return

4. OBSERVE RESULTS
   - Restart Kiro
   - Check if fake models appear in model selection UI
   - Look for models named:
     * "Custom Test Model 1"
     * "Custom Test Model 2"

5. DOCUMENT FINDINGS
   - If fake models appear: Kiro has DYNAMIC model list
     → We can add custom models via API injection
     → Strategy: Inject our custom models into the list
   
   - If fake models DON'T appear: Kiro has HARDCODED model list
     → We must replace existing models when they're selected
     → Strategy: Intercept model selection and swap backend

ALTERNATIVE APPROACH (if no model endpoint found):

If Kiro doesn't fetch models via API, they might be:
- Hardcoded in the binary
- Loaded from local config file
- Embedded in the initial authentication response

In this case, we should:
1. Search Kiro's resources folder for model configs
2. Check authentication responses for model lists
3. Use model replacement strategy instead of injection

="*60
"""
    
    return instructions


def main():
    """Main test function"""
    
    print("\n" + "="*60)
    print("MODEL LIST INJECTION TEST")
    print("="*60)
    print("\nThis tool helps determine if Kiro has a hardcoded or dynamic model list.\n")
    
    # Step 1: Create fake models
    print("Step 1: Creating fake model list...")
    fake_models = create_fake_model_list_response()
    print(f"✓ Created {len(fake_models)} fake models")
    
    # Step 2: Generate test variations
    print("\nStep 2: Generating test variations...")
    variations = create_model_list_event(fake_models)
    
    # Step 3: Save test files
    print("\nStep 3: Saving test files...")
    output_dir = save_test_injections(variations)
    
    # Step 4: Show instructions
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("\n1. First, we need to discover if Kiro fetches models via API")
    print("   Run: python _kiropipe/devtools/discover_endpoints.py")
    print("\n2. Enable debug mode and monitor traffic while using Kiro")
    print("\n3. Look for model-related API calls")
    print("\n4. Follow the detailed instructions below")
    
    # Save instructions
    instructions = create_injection_instructions()
    instructions_file = output_dir / "INSTRUCTIONS.txt"
    instructions_file.write_text(instructions)
    print(f"\n✓ Detailed instructions saved to: {instructions_file}")
    
    print("\n" + "="*60)
    print("✓ TEST PREPARATION COMPLETE")
    print("="*60)
    print(f"\nTest files: {output_dir}")
    print(f"Instructions: {instructions_file}")
    print("\nRead INSTRUCTIONS.txt for the complete testing procedure.")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
