#!/usr/bin/env python3
"""
Retry Handler with Exponential Backoff
Handles API call retries with exponential backoff and jitter
"""

import time
import random
import asyncio
from typing import Callable, Any, Optional, Dict
from functools import wraps


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter_factor: float = 0.1,
        retry_on_status: tuple = (429, 500, 502, 503, 504),
        timeout: float = 300.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        self.retry_on_status = retry_on_status
        self.timeout = timeout


class RetryHandler:
    """Handles retry logic with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay with exponential backoff and jitter
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * 2^attempt
        delay = min(self.config.base_delay * (2 ** attempt), self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * self.config.jitter_factor)
        
        return delay + jitter
    
    def should_retry(self, status_code: int, attempt: int, exception: Optional[Exception] = None) -> bool:
        """
        Determine if request should be retried
        
        Args:
            status_code: HTTP status code (0 if exception)
            attempt: Current attempt number (0-indexed)
            exception: Exception that occurred (if any)
        
        Returns:
            True if should retry, False otherwise
        """
        # Check max retries
        if attempt >= self.config.max_retries:
            return False
        
        # Retry on network errors
        if exception is not None:
            # Retry on connection errors, timeouts, etc.
            return True
        
        # Retry on specific status codes
        return status_code in self.config.retry_on_status
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic (synchronous)
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            Function result
        
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # Check if result has status_code (for HTTP responses)
                if hasattr(result, 'status_code'):
                    if self.should_retry(result.status_code, attempt):
                        if attempt < self.config.max_retries:
                            delay = self.calculate_delay(attempt)
                            print(f"[Retry] Attempt {attempt + 1} failed with status {result.status_code}. Retrying in {delay:.2f}s...")
                            time.sleep(delay)
                            continue
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if self.should_retry(0, attempt, e):
                    if attempt < self.config.max_retries:
                        delay = self.calculate_delay(attempt)
                        print(f"[Retry] Attempt {attempt + 1} failed with error: {e}. Retrying in {delay:.2f}s...")
                        time.sleep(delay)
                        continue
                
                # Don't retry, raise immediately
                raise
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        
        return result
    
    async def execute_with_retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with retry logic
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
        
        Returns:
            Function result
        
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                # Check if result has status_code (for HTTP responses)
                if hasattr(result, 'status_code'):
                    if self.should_retry(result.status_code, attempt):
                        if attempt < self.config.max_retries:
                            delay = self.calculate_delay(attempt)
                            print(f"[Retry] Attempt {attempt + 1} failed with status {result.status_code}. Retrying in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            continue
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if self.should_retry(0, attempt, e):
                    if attempt < self.config.max_retries:
                        delay = self.calculate_delay(attempt)
                        print(f"[Retry] Attempt {attempt + 1} failed with error: {e}. Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                        continue
                
                # Don't retry, raise immediately
                raise
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        
        return result


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to functions
    
    Usage:
        @with_retry(RetryConfig(max_retries=5))
        def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        handler = RetryHandler(config)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return handler.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


def with_retry_async(config: Optional[RetryConfig] = None):
    """
    Decorator for adding retry logic to async functions
    
    Usage:
        @with_retry_async(RetryConfig(max_retries=5))
        async def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        handler = RetryHandler(config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute_with_retry_async(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# Test function
if __name__ == '__main__':
    print("Testing Retry Handler\n")
    print("="*60)
    
    # Test 1: Successful call (no retry)
    print("\nTest 1: Successful call")
    print("-"*60)
    
    call_count = 0
    
    @with_retry(RetryConfig(max_retries=3))
    def successful_call():
        global call_count
        call_count += 1
        print(f"Call #{call_count}")
        return "Success!"
    
    result = successful_call()
    print(f"Result: {result}")
    print(f"Total calls: {call_count}")
    assert call_count == 1, "Should only call once"
    
    # Test 2: Retry on exception
    print("\nTest 2: Retry on exception")
    print("-"*60)
    
    call_count = 0
    
    @with_retry(RetryConfig(max_retries=3, base_delay=0.1))
    def failing_call():
        global call_count
        call_count += 1
        print(f"Call #{call_count}")
        if call_count < 3:
            raise ConnectionError("Network error")
        return "Success after retries!"
    
    result = failing_call()
    print(f"Result: {result}")
    print(f"Total calls: {call_count}")
    assert call_count == 3, "Should retry twice and succeed on third"
    
    # Test 3: Max retries exhausted
    print("\nTest 3: Max retries exhausted")
    print("-"*60)
    
    call_count = 0
    
    @with_retry(RetryConfig(max_retries=2, base_delay=0.1))
    def always_failing_call():
        global call_count
        call_count += 1
        print(f"Call #{call_count}")
        raise ConnectionError("Network error")
    
    try:
        result = always_failing_call()
        assert False, "Should have raised exception"
    except ConnectionError as e:
        print(f"Exception raised: {e}")
        print(f"Total calls: {call_count}")
        assert call_count == 3, "Should try 3 times (initial + 2 retries)"
    
    # Test 4: Exponential backoff calculation
    print("\nTest 4: Exponential backoff calculation")
    print("-"*60)
    
    handler = RetryHandler(RetryConfig(base_delay=1.0, max_delay=10.0, jitter_factor=0.1))
    
    for attempt in range(5):
        delay = handler.calculate_delay(attempt)
        expected_base = min(1.0 * (2 ** attempt), 10.0)
        print(f"Attempt {attempt}: {delay:.3f}s (base: {expected_base:.1f}s)")
        assert delay >= expected_base, "Delay should be >= base"
        assert delay <= expected_base * 1.1, "Delay should be <= base * 1.1 (with jitter)"
    
    print("\n" + "="*60)
    print("\n✓ All retry handler tests passed!")
