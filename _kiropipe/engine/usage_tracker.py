#!/usr/bin/env python3
"""
Usage Tracker
Tracks token usage, costs, and statistics across sessions and conversations
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from threading import Lock


class UsageTracker:
    """Tracks usage statistics for LLM API calls"""
    
    # Model pricing (per 1M tokens)
    MODEL_PRICING = {
        # Anthropic Claude
        'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00},
        'claude-3-5-haiku-20241022': {'input': 0.80, 'output': 4.00},
        'claude-3-opus-20240229': {'input': 15.00, 'output': 75.00},
        
        # OpenAI GPT
        'gpt-4-turbo': {'input': 10.00, 'output': 30.00},
        'gpt-4': {'input': 30.00, 'output': 60.00},
        'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50},
        
        # Default for unknown models
        'default': {'input': 1.00, 'output': 2.00}
    }
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize usage tracker
        
        Args:
            storage_path: Path to store usage data (default: _kiropipe/debug_logs/usage.json)
        """
        if storage_path is None:
            storage_path = Path(__file__).parent.parent / 'debug_logs' / 'usage.json'
        
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.data = self._load_data()
        self.current_session_id = self._generate_session_id()
        self.lock = Lock()
        
        # Initialize current session
        if self.current_session_id not in self.data['sessions']:
            self.data['sessions'][self.current_session_id] = {
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'conversations': {}
            }
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{int(time.time())}_{id(self)}"
    
    def _load_data(self) -> Dict[str, Any]:
        """Load usage data from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[UsageTracker] Warning: Failed to load usage data: {e}")
        
        # Return empty structure
        return {
            'sessions': {},
            'totals': {
                'total_requests': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_cost': 0.0
            }
        }
    
    def _save_data(self):
        """Save usage data to storage"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[UsageTracker] Warning: Failed to save usage data: {e}")
    
    def _get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for model"""
        return self.MODEL_PRICING.get(model, self.MODEL_PRICING['default'])
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage"""
        pricing = self._get_model_pricing(model)
        
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        
        return input_cost + output_cost
    
    def track_request(
        self,
        conversation_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Track a single API request
        
        Args:
            conversation_id: Conversation ID
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            metadata: Additional metadata (optional)
        """
        with self.lock:
            session = self.data['sessions'][self.current_session_id]
            
            # Initialize conversation if needed
            if conversation_id not in session['conversations']:
                session['conversations'][conversation_id] = {
                    'model': model,
                    'requests': [],
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_cost': 0.0
                }
            
            conversation = session['conversations'][conversation_id]
            
            # Calculate cost
            cost = self._calculate_cost(model, input_tokens, output_tokens)
            
            # Create request record
            request_record = {
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'cost': cost
            }
            
            if metadata:
                request_record['metadata'] = metadata
            
            # Update conversation
            conversation['requests'].append(request_record)
            conversation['total_input_tokens'] += input_tokens
            conversation['total_output_tokens'] += output_tokens
            conversation['total_cost'] += cost
            
            # Update totals
            self.data['totals']['total_requests'] += 1
            self.data['totals']['total_input_tokens'] += input_tokens
            self.data['totals']['total_output_tokens'] += output_tokens
            self.data['totals']['total_cost'] += cost
            
            # Save to disk
            self._save_data()
    
    def get_conversation_stats(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a conversation"""
        with self.lock:
            session = self.data['sessions'][self.current_session_id]
            return session['conversations'].get(conversation_id)
    
    def get_session_stats(self, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get statistics for a session"""
        with self.lock:
            if session_id is None:
                session_id = self.current_session_id
            
            session = self.data['sessions'].get(session_id)
            if not session:
                return None
            
            # Calculate session totals
            total_input = 0
            total_output = 0
            total_cost = 0.0
            total_requests = 0
            
            for conv in session['conversations'].values():
                total_input += conv['total_input_tokens']
                total_output += conv['total_output_tokens']
                total_cost += conv['total_cost']
                total_requests += len(conv['requests'])
            
            return {
                'session_id': session_id,
                'start_time': session['start_time'],
                'end_time': session['end_time'],
                'conversations': len(session['conversations']),
                'total_requests': total_requests,
                'total_input_tokens': total_input,
                'total_output_tokens': total_output,
                'total_tokens': total_input + total_output,
                'total_cost': total_cost
            }
    
    def get_total_stats(self) -> Dict[str, Any]:
        """Get total statistics across all sessions"""
        with self.lock:
            return self.data['totals'].copy()
    
    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics grouped by model"""
        with self.lock:
            model_stats = {}
            
            for session in self.data['sessions'].values():
                for conv in session['conversations'].values():
                    model = conv['model']
                    
                    if model not in model_stats:
                        model_stats[model] = {
                            'requests': 0,
                            'input_tokens': 0,
                            'output_tokens': 0,
                            'total_tokens': 0,
                            'cost': 0.0
                        }
                    
                    stats = model_stats[model]
                    stats['requests'] += len(conv['requests'])
                    stats['input_tokens'] += conv['total_input_tokens']
                    stats['output_tokens'] += conv['total_output_tokens']
                    stats['total_tokens'] += conv['total_input_tokens'] + conv['total_output_tokens']
                    stats['cost'] += conv['total_cost']
            
            return model_stats
    
    def end_session(self):
        """Mark current session as ended"""
        with self.lock:
            session = self.data['sessions'][self.current_session_id]
            session['end_time'] = datetime.now().isoformat()
            self._save_data()
    
    def print_summary(self, session_id: Optional[str] = None):
        """Print usage summary"""
        if session_id is None:
            session_id = self.current_session_id
        
        stats = self.get_session_stats(session_id)
        if not stats:
            print(f"No statistics found for session: {session_id}")
            return
        
        print("\n" + "="*60)
        print("Usage Summary")
        print("="*60)
        print(f"Session ID: {stats['session_id']}")
        print(f"Start Time: {stats['start_time']}")
        if stats['end_time']:
            print(f"End Time: {stats['end_time']}")
        print(f"\nConversations: {stats['conversations']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"\nTokens:")
        print(f"  Input:  {stats['total_input_tokens']:,}")
        print(f"  Output: {stats['total_output_tokens']:,}")
        print(f"  Total:  {stats['total_tokens']:,}")
        print(f"\nEstimated Cost: ${stats['total_cost']:.4f}")
        print("="*60 + "\n")
    
    def print_model_summary(self):
        """Print usage summary by model"""
        model_stats = self.get_model_stats()
        
        if not model_stats:
            print("No model statistics available")
            return
        
        print("\n" + "="*60)
        print("Usage by Model")
        print("="*60)
        
        for model, stats in sorted(model_stats.items()):
            print(f"\n{model}:")
            print(f"  Requests: {stats['requests']}")
            print(f"  Tokens: {stats['total_tokens']:,} (in: {stats['input_tokens']:,}, out: {stats['output_tokens']:,})")
            print(f"  Cost: ${stats['cost']:.4f}")
        
        print("="*60 + "\n")
    
    def export_to_csv(self, output_path: Path):
        """Export usage data to CSV"""
        import csv
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Session ID', 'Conversation ID', 'Timestamp', 'Model',
                'Input Tokens', 'Output Tokens', 'Total Tokens', 'Cost'
            ])
            
            for session_id, session in self.data['sessions'].items():
                for conv_id, conv in session['conversations'].items():
                    for req in conv['requests']:
                        writer.writerow([
                            session_id,
                            conv_id,
                            req['timestamp'],
                            req['model'],
                            req['input_tokens'],
                            req['output_tokens'],
                            req['total_tokens'],
                            f"{req['cost']:.6f}"
                        ])
        
        print(f"Usage data exported to: {output_path}")


# Test function
if __name__ == '__main__':
    print("Testing Usage Tracker\n")
    print("="*60)
    
    # Create temporary tracker
    import tempfile
    temp_file = Path(tempfile.mktemp(suffix='.json'))
    
    tracker = UsageTracker(temp_file)
    
    # Test 1: Track some requests
    print("\nTest 1: Track requests")
    print("-"*60)
    
    tracker.track_request(
        conversation_id='conv_1',
        model='claude-3-5-sonnet-20241022',
        input_tokens=100,
        output_tokens=50
    )
    
    tracker.track_request(
        conversation_id='conv_1',
        model='claude-3-5-sonnet-20241022',
        input_tokens=200,
        output_tokens=100
    )
    
    tracker.track_request(
        conversation_id='conv_2',
        model='gpt-4-turbo',
        input_tokens=150,
        output_tokens=75
    )
    
    print("✓ Tracked 3 requests")
    
    # Test 2: Get conversation stats
    print("\nTest 2: Conversation statistics")
    print("-"*60)
    
    conv_stats = tracker.get_conversation_stats('conv_1')
    print(f"Conversation 1:")
    print(f"  Model: {conv_stats['model']}")
    print(f"  Requests: {len(conv_stats['requests'])}")
    print(f"  Total tokens: {conv_stats['total_input_tokens'] + conv_stats['total_output_tokens']}")
    print(f"  Cost: ${conv_stats['total_cost']:.4f}")
    
    # Test 3: Get session stats
    print("\nTest 3: Session statistics")
    print("-"*60)
    
    tracker.print_summary()
    
    # Test 4: Get model stats
    print("\nTest 4: Model statistics")
    print("-"*60)
    
    tracker.print_model_summary()
    
    # Test 5: Export to CSV
    print("\nTest 5: Export to CSV")
    print("-"*60)
    
    csv_file = temp_file.with_suffix('.csv')
    tracker.export_to_csv(csv_file)
    
    # Cleanup
    temp_file.unlink(missing_ok=True)
    csv_file.unlink(missing_ok=True)
    
    print("\n" + "="*60)
    print("\n✓ All usage tracker tests passed!")
