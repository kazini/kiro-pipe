#!/usr/bin/env python3
"""
Test All Format Translations
Comprehensive validation of both Anthropic and OpenAI translations
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
import test_anthropic_translation
import test_openai_translation
import test_with_real_samples
import validate_format


def main():
    """Run all format validation tests"""
    print("\n" + "="*60)
    print("COMPREHENSIVE FORMAT VALIDATION")
    print("="*60)
    
    results = []
    
    # Test 1: Anthropic Translation
    print("\n" + "="*60)
    print("1. ANTHROPIC TRANSLATION TESTS")
    print("="*60)
    try:
        result = test_anthropic_translation.run_all_tests()
        results.append(("Anthropic Translation", result == 0))
    except Exception as e:
        print(f"Error: {e}")
        results.append(("Anthropic Translation", False))
    
    # Test 2: OpenAI Translation
    print("\n" + "="*60)
    print("2. OPENAI TRANSLATION TESTS")
    print("="*60)
    try:
        result = test_openai_translation.run_all_tests()
        results.append(("OpenAI Translation", result == 0))
    except Exception as e:
        print(f"Error: {e}")
        results.append(("OpenAI Translation", False))
    
    # Test 3: Real Sample Validation
    print("\n" + "="*60)
    print("3. REAL SAMPLE VALIDATION")
    print("="*60)
    try:
        result = test_with_real_samples.main()
        results.append(("Real Sample Validation", result == 0))
    except Exception as e:
        print(f"Error: {e}")
        results.append(("Real Sample Validation", False))
    
    # Test 4: Format Validation
    print("\n" + "="*60)
    print("4. AWS Q FORMAT VALIDATION")
    print("="*60)
    try:
        validate_format.main()
        results.append(("AWS Q Format", True))
    except Exception as e:
        print(f"Error: {e}")
        results.append(("AWS Q Format", False))
    
    # Final Summary
    print("\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}{status}{reset} - {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("\033[92m✓ ALL TESTS PASSED!\033[0m")
        print("="*60)
        print("\nFormat translation is working correctly:")
        print("  ✓ AWS Q → Anthropic translation")
        print("  ✓ Anthropic → AWS Q translation")
        print("  ✓ AWS Q → OpenAI translation")
        print("  ✓ OpenAI → AWS Q translation")
        print("  ✓ Binary format encoding/decoding")
        print("  ✓ Tool use format")
        print("  ✓ Usage tracking")
        print("\nReady for integration into kiropipe.py!")
        return 0
    else:
        print("\033[91m✗ SOME TESTS FAILED\033[0m")
        print("="*60)
        failed_tests = [name for name, passed in results if not passed]
        print(f"\nFailed tests: {', '.join(failed_tests)}")
        print("\nPlease review the errors above and fix the issues.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
