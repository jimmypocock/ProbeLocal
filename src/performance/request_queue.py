"""Request queuing system for handling concurrent operations"""
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)


class RequestStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Request:
    id: str
    type: str
    data: Dict[str, Any]
    status: RequestStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    priority: int = 0  # Higher priority = processed first


class RequestQueueManager:
    """Manages request queue with priority and concurrency control"""
    
    def __init__(self, max_concurrent: int = 3, max_queue_size: int = 100):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        
        # Thread-safe queues
        self._pending_queue = deque()
        self._processing = {}
        self._completed = {}
        
        # Locks for thread safety
        self._queue_lock = threading.Lock()
        self._processing_lock = threading.Lock()
        self._completed_lock = threading.Lock()
        
        # Executor for processing requests
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
        # Request handlers
        self._handlers = {}
        
        # Start background processor
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_queue)
        self._processor_thread.daemon = True
        self._processor_thread.start()
    
    def register_handler(self, request_type: str, handler: Callable) -> None:
        """Register a handler for a request type"""
        self._handlers[request_type] = handler
    
    def submit_request(
        self, 
        request_type: str, 
        data: Dict[str, Any], 
        priority: int = 0
    ) -> str:
        """Submit a new request to the queue"""
        request_id = str(uuid.uuid4())
        
        request = Request(
            id=request_id,
            type=request_type,
            data=data,
            status=RequestStatus.PENDING,
            created_at=time.time(),
            priority=priority
        )
        
        with self._queue_lock:
            if len(self._pending_queue) >= self.max_queue_size:
                raise ValueError("Request queue is full")
            
            # Insert based on priority
            inserted = False
            for i, req in enumerate(self._pending_queue):
                if request.priority > req.priority:
                    self._pending_queue.insert(i, request)
                    inserted = True
                    break
            
            if not inserted:
                self._pending_queue.append(request)
        
        logger.info(f"Request {request_id} queued with priority {priority}")
        return request_id
    
    def get_request_status(self, request_id: str) -> Optional[Request]:
        """Get the status of a request"""
        # Check processing
        with self._processing_lock:
            if request_id in self._processing:
                return self._processing[request_id]
        
        # Check completed
        with self._completed_lock:
            if request_id in self._completed:
                return self._completed[request_id]
        
        # Check pending
        with self._queue_lock:
            for req in self._pending_queue:
                if req.id == request_id:
                    return req
        
        return None
    
    def get_queue_position(self, request_id: str) -> int:
        """Get position in queue (0 if not in queue)"""
        with self._queue_lock:
            for i, req in enumerate(self._pending_queue):
                if req.id == request_id:
                    return i + 1
        return 0
    
    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request"""
        with self._queue_lock:
            for i, req in enumerate(self._pending_queue):
                if req.id == request_id:
                    req.status = RequestStatus.CANCELLED
                    del self._pending_queue[i]
                    
                    # Use completed lock when accessing _completed
                    with self._completed_lock:
                        self._completed[request_id] = req
                    return True
        return False
    
    def _process_queue(self) -> None:
        """Background thread to process queue"""
        while self._running:
            # Check if we can process more requests
            with self._processing_lock:
                processing_count = len(self._processing)
            
            if processing_count < self.max_concurrent:
                # Get next request
                request = None
                with self._queue_lock:
                    if self._pending_queue:
                        request = self._pending_queue.popleft()
                
                if request:
                    # Start processing
                    self._executor.submit(self._process_request, request)
            
            time.sleep(0.1)  # Small delay to prevent busy waiting
    
    def _process_request(self, request: Request) -> None:
        """Process a single request"""
        try:
            # Update status
            request.status = RequestStatus.PROCESSING
            request.started_at = time.time()
            
            with self._processing_lock:
                self._processing[request.id] = request
            
            logger.info(f"Processing request {request.id} of type {request.type}")
            
            # Get handler
            handler = self._handlers.get(request.type)
            if not handler:
                raise ValueError(f"No handler registered for request type: {request.type}")
            
            # Execute handler
            result = handler(**request.data)
            
            # Update request
            request.status = RequestStatus.COMPLETED
            request.completed_at = time.time()
            request.result = result
            
            logger.info(f"Request {request.id} completed in {request.completed_at - request.started_at:.2f}s")
            
        except Exception as e:
            logger.error(f"Request {request.id} failed: {str(e)}")
            request.status = RequestStatus.FAILED
            request.completed_at = time.time()
            request.error = str(e)
        
        finally:
            # Move to completed
            with self._processing_lock:
                del self._processing[request.id]
            
            # Use a separate lock for completed requests
            with self._completed_lock:
                self._completed[request.id] = request
                
                # Clean old completed requests (keep last 100)
                if len(self._completed) > 100:
                    oldest_id = min(self._completed.keys(), 
                                  key=lambda k: self._completed[k].completed_at)
                    del self._completed[oldest_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._queue_lock:
            pending_count = len(self._pending_queue)
        
        with self._processing_lock:
            processing_count = len(self._processing)
        
        with self._completed_lock:
            completed_count = len(self._completed)
            
            # Calculate average processing time
            avg_time = 0
            completed_requests = [r for r in self._completed.values() 
                                if r.status == RequestStatus.COMPLETED and r.started_at]
        if completed_requests:
            times = [r.completed_at - r.started_at for r in completed_requests]
            avg_time = sum(times) / len(times)
        
        return {
            'pending': pending_count,
            'processing': processing_count,
            'completed': completed_count,
            'avg_processing_time': avg_time,
            'max_concurrent': self.max_concurrent,
            'queue_capacity': f"{pending_count}/{self.max_queue_size}"
        }
    
    def shutdown(self) -> None:
        """Shutdown the queue manager"""
        self._running = False
        self._processor_thread.join()
        self._executor.shutdown(wait=True)


# Global request queue instance
request_queue = RequestQueueManager()


def queue_request(request_type: str, data: Dict[str, Any], priority: int = 0) -> str:
    """Helper function to queue a request"""
    return request_queue.submit_request(request_type, data, priority)


def get_request_result(request_id: str, timeout: float = 60) -> Any:
    """Wait for and get request result"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = request_queue.get_request_status(request_id)
        
        if not status:
            raise ValueError(f"Request {request_id} not found")
        
        if status.status == RequestStatus.COMPLETED:
            return status.result
        
        if status.status == RequestStatus.FAILED:
            raise Exception(f"Request failed: {status.error}")
        
        if status.status == RequestStatus.CANCELLED:
            raise Exception("Request was cancelled")
        
        time.sleep(0.1)
    
    raise TimeoutError(f"Request {request_id} timed out after {timeout}s")