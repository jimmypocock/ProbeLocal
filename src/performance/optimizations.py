"""Performance optimization utilities"""
import time
import functools
from typing import Any, Callable, Dict, Optional, List
import hashlib
import json
from collections import OrderedDict
import streamlit as st


class Debouncer:
    """Debounce function calls to prevent excessive updates"""
    
    def __init__(self, delay: float = 0.3):
        self.delay = delay
        self.timers = {}
    
    def debounce(self, key: str, func: Callable, *args, **kwargs) -> None:
        """Debounce a function call"""
        current_time = time.time()
        
        # Cancel previous timer if exists
        if key in self.timers:
            # Check if enough time has passed
            if current_time - self.timers[key]['time'] < self.delay:
                # Update the function to call and time
                self.timers[key] = {
                    'time': current_time,
                    'func': func,
                    'args': args,
                    'kwargs': kwargs
                }
                return
        
        # Execute immediately if no recent call
        self.timers[key] = {'time': current_time}
        func(*args, **kwargs)


class LRUCache:
    """Least Recently Used cache for query results"""
    
    def __init__(self, max_size: int = 100):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def _make_key(self, *args, **kwargs) -> str:
        """Create a cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, *args, **kwargs) -> Optional[Any]:
        """Get item from cache"""
        key = self._make_key(*args, **kwargs)
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]['value']
        return None
    
    def set(self, value: Any, *args, **kwargs) -> None:
        """Set item in cache"""
        key = self._make_key(*args, **kwargs)
        
        # Remove oldest item if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
        self.cache.move_to_end(key)
    
    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()


def memoize_result(ttl: int = 300):
    """Decorator to memoize function results with TTL"""
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = hashlib.md5(
                f"{func.__name__}:{args}:{kwargs}".encode()
            ).hexdigest()
            
            # Check cache
            if key in cache:
                value, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return value
            
            # Compute result
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            
            # Clean old entries
            current_time = time.time()
            cache_copy = dict(cache)
            for k, (_, ts) in cache_copy.items():
                if current_time - ts > ttl:
                    del cache[k]
            
            return result
        
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    
    return decorator


class BatchProcessor:
    """Batch multiple operations for efficiency"""
    
    def __init__(self, batch_size: int = 10, timeout: float = 0.1):
        self.batch_size = batch_size
        self.timeout = timeout
        self.pending = []
        self.last_process_time = time.time()
    
    def add(self, item: Any) -> None:
        """Add item to batch"""
        self.pending.append(item)
        
        # Process if batch is full or timeout reached
        if (len(self.pending) >= self.batch_size or 
            time.time() - self.last_process_time > self.timeout):
            self.process()
    
    def process(self) -> List[Any]:
        """Process all pending items"""
        if not self.pending:
            return []
        
        items = self.pending[:]
        self.pending.clear()
        self.last_process_time = time.time()
        
        return items


def optimize_rerun(key: str, cooldown: float = 0.5) -> bool:
    """Prevent excessive reruns"""
    if 'rerun_timestamps' not in st.session_state:
        st.session_state.rerun_timestamps = {}
    
    current_time = time.time()
    last_rerun = st.session_state.rerun_timestamps.get(key, 0)
    
    if current_time - last_rerun > cooldown:
        st.session_state.rerun_timestamps[key] = current_time
        return True
    
    return False


class StateManager:
    """Optimized state management to prevent unnecessary updates"""
    
    @staticmethod
    def update_if_changed(key: str, new_value: Any) -> bool:
        """Update session state only if value changed"""
        if key not in st.session_state:
            st.session_state[key] = new_value
            return True
        
        if st.session_state[key] != new_value:
            st.session_state[key] = new_value
            return True
        
        return False
    
    @staticmethod
    def batch_update(updates: Dict[str, Any]) -> bool:
        """Update multiple state values at once"""
        changed = False
        for key, value in updates.items():
            if StateManager.update_if_changed(key, value):
                changed = True
        return changed


# Request queue for handling concurrent operations
class RequestQueue:
    """Queue for managing concurrent requests"""
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        if 'request_queue' not in st.session_state:
            st.session_state.request_queue = []
        if 'active_requests' not in st.session_state:
            st.session_state.active_requests = 0
    
    def add_request(self, request_id: str, request_data: Dict) -> bool:
        """Add request to queue"""
        if st.session_state.active_requests < self.max_concurrent:
            st.session_state.active_requests += 1
            return True
        else:
            st.session_state.request_queue.append({
                'id': request_id,
                'data': request_data,
                'timestamp': time.time()
            })
            return False
    
    def complete_request(self, request_id: str) -> Optional[Dict]:
        """Mark request as complete and get next from queue"""
        st.session_state.active_requests = max(0, st.session_state.active_requests - 1)
        
        if st.session_state.request_queue:
            return st.session_state.request_queue.pop(0)
        
        return None
    
    def get_queue_position(self, request_id: str) -> int:
        """Get position in queue"""
        for i, req in enumerate(st.session_state.request_queue):
            if req['id'] == request_id:
                return i + 1
        return 0