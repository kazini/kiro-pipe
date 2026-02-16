#!/usr/bin/env python3
"""
Quota Manager
Tracks API quota usage and manages free/paid model variants
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading


class QuotaManager:
    """Manages quota tracking and caching for API providers"""
    
    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize quota manager
        
        Args:
            cache_file: Path to quota cache file (defaults to _kiropipe/engine/quota_cache.json)
        """
        if cache_file is None:
            # Store in engine directory
            cache_file = Path(__file__).parent / 'quota_cache.json'
        
        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self._load_cache()
    
    def _load_cache(self):
        """Load quota cache from disk"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load quota cache: {e}")
            self.cache = {}
    
    def _save_cache(self):
        """Save quota cache to disk"""
        try:
            # Clean up expired entries before saving
            self._cleanup_expired_entries()
            
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save quota cache: {e}")
    
    def _cleanup_expired_entries(self):
        """Remove entries where all reset times have passed and quota is restored"""
        now = datetime.utcnow()
        expired_keys = []
        
        for model_id, entry in self.cache.items():
            # Check if all reset times have passed
            requests_expired = True
            tokens_expired = True
            
            # Check requests reset
            if 'requests_reset_at' in entry:
                try:
                    reset_time = datetime.fromisoformat(entry['requests_reset_at'].replace('Z', ''))
                    if now < reset_time:
                        requests_expired = False
                except:
                    pass
            
            # Check tokens reset
            if 'tokens_reset_at' in entry:
                try:
                    reset_time = datetime.fromisoformat(entry['tokens_reset_at'].replace('Z', ''))
                    if now < reset_time:
                        tokens_expired = False
                except:
                    pass
            
            # If both have expired (or don't exist), and quota is fully restored, mark for deletion
            if requests_expired and tokens_expired:
                # Check if quota is at 100% (fully restored)
                requests_full = False
                tokens_full = False
                
                if 'requests_limit' in entry and 'requests_remaining' in entry:
                    requests_full = entry['requests_remaining'] >= entry['requests_limit']
                else:
                    requests_full = True  # No data, consider it restored
                
                if 'tokens_limit' in entry and 'tokens_remaining' in entry:
                    tokens_full = entry['tokens_remaining'] >= entry['tokens_limit']
                else:
                    tokens_full = True  # No data, consider it restored
                
                # Only delete if fully restored (or no quota data exists)
                if requests_full and tokens_full:
                    # Keep entry for 7 days after restoration for historical reference
                    last_updated = entry.get('last_updated', '')
                    try:
                        updated_time = datetime.fromisoformat(last_updated.replace('Z', ''))
                        days_since_update = (now - updated_time).days
                        if days_since_update > 7:
                            expired_keys.append(model_id)
                    except:
                        # If we can't parse the date, keep it
                        pass
        
        # Remove expired entries
        for key in expired_keys:
            del self.cache[key]
            if expired_keys:
                print(f"Cleaned up {len(expired_keys)} expired quota entries")
    
    def update_from_headers(self, model_id: str, headers: Dict[str, str], overage_cost: float = 0.0):
        """
        Update quota info from response headers
        
        Supports multiple header formats:
        - Groq: x-ratelimit-limit-requests, x-ratelimit-remaining-requests, x-ratelimit-reset-requests
        - OpenAI/Standard: x-ratelimit-limit, x-ratelimit-remaining, x-ratelimit-reset
        - OpenRouter: x-ratelimit-requests-limit, x-ratelimit-requests-remaining
        
        Args:
            model_id: Model identifier
            headers: Response headers from API call
            overage_cost: Cost per 1M tokens if quota exceeded
        """
        with self.lock:
            now = datetime.utcnow().isoformat() + 'Z'
            
            # Initialize model entry if not exists
            if model_id not in self.cache:
                self.cache[model_id] = {
                    'last_updated': now,
                    'overage_cost': overage_cost
                }
            
            entry = self.cache[model_id]
            entry['last_updated'] = now
            entry['overage_cost'] = overage_cost
            
            # Normalize header names to lowercase for case-insensitive matching
            headers_lower = {k.lower(): v for k, v in headers.items()}
            
            # Parse Groq-style headers (requests)
            if 'x-ratelimit-limit-requests' in headers_lower:
                entry['requests_limit'] = int(headers_lower.get('x-ratelimit-limit-requests', 0))
                entry['requests_remaining'] = int(headers_lower.get('x-ratelimit-remaining-requests', 0))
                
                reset_str = headers_lower.get('x-ratelimit-reset-requests', '')
                if reset_str:
                    entry['requests_reset_at'] = self._parse_reset_time(reset_str)
            
            # Parse Groq-style headers (tokens)
            if 'x-ratelimit-limit-tokens' in headers_lower:
                entry['tokens_limit'] = int(headers_lower.get('x-ratelimit-limit-tokens', 0))
                entry['tokens_remaining'] = int(headers_lower.get('x-ratelimit-remaining-tokens', 0))
                
                reset_str = headers_lower.get('x-ratelimit-reset-tokens', '')
                if reset_str:
                    entry['tokens_reset_at'] = self._parse_reset_time(reset_str)
            
            # Parse OpenRouter-style headers
            if 'x-ratelimit-requests-limit' in headers_lower:
                entry['requests_limit'] = int(headers_lower.get('x-ratelimit-requests-limit', 0))
                entry['requests_remaining'] = int(headers_lower.get('x-ratelimit-requests-remaining', 0))
                
                # Check for reset period (daily, weekly, monthly)
                reset_period = headers_lower.get('x-ratelimit-reset', '') or headers_lower.get('x-ratelimit-reset-period', '')
                if reset_period:
                    entry['requests_reset_at'] = self._parse_reset_time(reset_period)
            
            # Parse standard headers (OpenAI, etc.)
            if 'x-ratelimit-limit' in headers_lower and 'x-ratelimit-limit-requests' not in headers_lower:
                entry['requests_limit'] = int(headers_lower.get('x-ratelimit-limit', 0))
                entry['requests_remaining'] = int(headers_lower.get('x-ratelimit-remaining', 0))
                
                reset_str = headers_lower.get('x-ratelimit-reset', '')
                if reset_str:
                    entry['requests_reset_at'] = self._parse_reset_time(reset_str)
            
            self._save_cache()
    
    def _parse_reset_time(self, reset_str: str) -> str:
        """
        Parse reset time string to ISO timestamp
        
        Supports multiple formats:
        1. Relative time: "2m59.56s", "23h15m" (Groq format)
        2. Unix timestamp: "1704067200" (standard format)
        3. Seconds: "30" (Retry-After format)
        4. Period: "daily", "weekly", "monthly" (OpenRouter format)
        
        Args:
            reset_str: Reset time string
        
        Returns:
            ISO timestamp string
        """
        try:
            reset_str_lower = reset_str.lower().strip()
            
            # Format 1: Period-based reset (OpenRouter)
            if reset_str_lower in ['daily', 'day']:
                # Reset at midnight UTC
                now = datetime.utcnow()
                tomorrow = now + timedelta(days=1)
                reset_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                return reset_time.isoformat() + 'Z'
            
            elif reset_str_lower in ['weekly', 'week']:
                # Reset at start of next week (Monday 00:00 UTC)
                now = datetime.utcnow()
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7  # If today is Monday, reset next Monday
                next_monday = now + timedelta(days=days_until_monday)
                reset_time = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
                return reset_time.isoformat() + 'Z'
            
            elif reset_str_lower in ['monthly', 'month']:
                # Reset at start of next month (1st day 00:00 UTC)
                now = datetime.utcnow()
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
                return next_month.isoformat() + 'Z'
            
            # Format 2: Try parsing as Unix timestamp (all digits)
            if reset_str.isdigit():
                timestamp = int(reset_str)
                # Check if it's a reasonable timestamp (after year 2000)
                if timestamp > 946684800:  # Jan 1, 2000
                    reset_time = datetime.utcfromtimestamp(timestamp)
                    return reset_time.isoformat() + 'Z'
                else:
                    # It's probably seconds until reset
                    reset_time = datetime.utcnow() + timedelta(seconds=timestamp)
                    return reset_time.isoformat() + 'Z'
            
            # Format 3: Relative time with units (Groq format)
            total_seconds = 0
            remaining = reset_str
            
            # Parse hours
            if 'h' in remaining:
                hours_part = remaining.split('h')[0]
                total_seconds += int(hours_part) * 3600
                remaining = remaining.split('h')[1]
            
            # Parse minutes
            if 'm' in remaining:
                minutes_part = remaining.split('m')[0]
                total_seconds += int(minutes_part) * 60
                remaining = remaining.split('m')[1]
            
            # Parse seconds
            if 's' in remaining:
                seconds_part = remaining.replace('s', '')
                if seconds_part:  # Only parse if there's a value
                    total_seconds += float(seconds_part)
            
            if total_seconds > 0:
                reset_time = datetime.utcnow() + timedelta(seconds=total_seconds)
                return reset_time.isoformat() + 'Z'
            
            # If we couldn't parse anything, default to 1 day
            raise ValueError(f"Could not parse reset time: {reset_str}")
            
        except Exception as e:
            print(f"Warning: Failed to parse reset time '{reset_str}': {e}")
            # Default to 1 day from now
            return (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
    
    def get_quota_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get quota information for a model
        
        This method checks timestamps on-demand (no background polling).
        When called, it compares current UTC time with cached reset timestamps
        and automatically restores quota if the reset time has passed.
        
        Args:
            model_id: Model identifier
        
        Returns:
            Quota info dict or None if not available
        """
        with self.lock:
            if model_id not in self.cache:
                return None
            
            entry = self.cache[model_id].copy()
            
            # Check if quota has reset (on-demand check using UTC time)
            now = datetime.utcnow()
            
            # Check requests reset
            if 'requests_reset_at' in entry:
                try:
                    reset_time = datetime.fromisoformat(entry['requests_reset_at'].replace('Z', ''))
                    if now >= reset_time:
                        # Quota has reset - restore to full
                        if 'requests_limit' in entry:
                            entry['requests_remaining'] = entry['requests_limit']
                            # Calculate next reset time based on the period
                            # For now, add 1 day (will be updated on next API call)
                            entry['requests_reset_at'] = (now + timedelta(days=1)).isoformat() + 'Z'
                            self.cache[model_id].update(entry)
                            self._save_cache()
                except Exception as e:
                    print(f"Warning: Failed to check requests reset time: {e}")
            
            # Check tokens reset
            if 'tokens_reset_at' in entry:
                try:
                    reset_time = datetime.fromisoformat(entry['tokens_reset_at'].replace('Z', ''))
                    if now >= reset_time:
                        # Quota has reset - restore to full
                        if 'tokens_limit' in entry:
                            entry['tokens_remaining'] = entry['tokens_limit']
                            # Calculate next reset time (1 minute for tokens)
                            entry['tokens_reset_at'] = (now + timedelta(minutes=1)).isoformat() + 'Z'
                            self.cache[model_id].update(entry)
                            self._save_cache()
                except Exception as e:
                    print(f"Warning: Failed to check tokens reset time: {e}")
            
            return entry
    
    def get_quota_percentage(self, model_id: str) -> Optional[int]:
        """
        Get quota usage percentage (0-100)
        
        Args:
            model_id: Model identifier
        
        Returns:
            Percentage used (0-100) or None if not available
        """
        info = self.get_quota_info(model_id)
        if not info:
            return None
        
        # Use requests quota as primary indicator
        if 'requests_limit' in info and 'requests_remaining' in info:
            limit = info['requests_limit']
            remaining = info['requests_remaining']
            if limit > 0:
                used = limit - remaining
                percentage = int((used / limit) * 100)
                return min(100, max(0, percentage))
        
        return None
    
    def is_quota_exhausted(self, model_id: str, threshold: int = 100) -> bool:
        """
        Check if quota is exhausted
        
        Args:
            model_id: Model identifier
            threshold: Percentage threshold (default 100)
        
        Returns:
            True if quota >= threshold
        """
        percentage = self.get_quota_percentage(model_id)
        if percentage is None:
            return False
        return percentage >= threshold
    
    def mark_switched_to_paid(self, model_id: str):
        """
        Mark that user has switched to paid variant
        
        Args:
            model_id: Model identifier
        """
        with self.lock:
            if model_id in self.cache:
                self.cache[model_id]['user_switched_to_paid'] = True
                self._save_cache()
    
    def has_switched_to_paid(self, model_id: str) -> bool:
        """
        Check if user has switched to paid variant
        
        Args:
            model_id: Model identifier
        
        Returns:
            True if user switched to paid
        """
        with self.lock:
            if model_id in self.cache:
                return self.cache[model_id].get('user_switched_to_paid', False)
            return False


# Global quota manager instance
_quota_manager = None


def get_quota_manager() -> QuotaManager:
    """Get global quota manager instance"""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager
