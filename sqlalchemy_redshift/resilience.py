"""
Production-grade error handling and resilience for Redshift SQLAlchemy Dialect
"""

import time
from logging import getLogger

logger = getLogger(__name__)

class ProductionErrorHandler:
    """Production-grade error handling for Redshift connections"""
    
    def __init__(self):
        self.transient_error_patterns = [
            'connection timeout',
            'temporary failure',
            'server temporarily unavailable',
            'connection reset',
            'network error',
            'timeout expired',
            'connection lost',
            'broken pipe'
        ]
    
    def is_transient_error(self, error):
        """Check if error is transient and should be retried"""
        error_msg = str(error).lower()
        return any(pattern in error_msg for pattern in self.transient_error_patterns)
    
    def is_disconnect_error(self, error):
        """Check if error indicates a disconnect"""
        error_msg = str(error).lower()
        disconnect_patterns = [
            'connection closed',
            'connection lost',
            'connection terminated',
            'server closed the connection',
            'broken pipe',
            'connection reset'
        ]
        return any(pattern in error_msg for pattern in disconnect_patterns)

class CircuitBreaker:
    """Circuit breaker for connection health monitoring"""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

def with_retry(max_retries=3, backoff_factor=2):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            error_handler = ProductionErrorHandler()
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries or not error_handler.is_transient_error(e):
                        raise
                    
                    # Exponential backoff
                    sleep_time = backoff_factor ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {sleep_time}s: {e}")
                    time.sleep(sleep_time)
            
        return wrapper
    return decorator