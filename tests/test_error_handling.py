"""
Tests for production-grade error handling and resilience features
"""
import pytest
from sqlalchemy_redshift.resilience import ProductionErrorHandler, CircuitBreaker
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector


class TestProductionErrorHandler:
    """Test production error handling"""
    
    def test_production_error_handler_creation(self):
        """Test ProductionErrorHandler can be created"""
        handler = ProductionErrorHandler()
        assert handler is not None
        assert hasattr(handler, 'is_transient_error')
        assert hasattr(handler, 'is_disconnect_error')

    def test_transient_error_detection(self):
        """Test transient error detection"""
        handler = ProductionErrorHandler()
        
        # Test transient error detection
        assert handler.is_transient_error(Exception("connection timeout"))
        assert not handler.is_transient_error(Exception("syntax error"))

    def test_disconnect_error_detection(self):
        """Test disconnect error detection"""
        handler = ProductionErrorHandler()
        
        # Test disconnect error detection
        assert handler.is_disconnect_error(Exception("connection lost"))
        assert not handler.is_disconnect_error(Exception("syntax error"))


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_creation(self):
        """Test CircuitBreaker can be created"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert breaker is not None
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 60

    def test_circuit_breaker_states(self):
        """Test circuit breaker state management"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Should start closed
        assert breaker.state == 'CLOSED'
        
        # Simulate failures
        breaker._on_failure()
        assert breaker.state == 'CLOSED'  # Still closed after 1 failure
        
        breaker._on_failure()
        assert breaker.state == 'OPEN'    # Open after 2 failures

    def test_circuit_breaker_success_recovery(self):
        """Test circuit breaker recovery on success"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Cause failures to open circuit
        breaker._on_failure()
        breaker._on_failure()
        assert breaker.state == 'OPEN'
        
        # Success should reset
        breaker._on_success()
        assert breaker.state == 'CLOSED'
        assert breaker.failure_count == 0


class TestDialectErrorHandling:
    """Test dialect integration with error handling"""
    
    def test_error_handler_integration(self):
        """Test error handler integration with dialect"""
        handler = ProductionErrorHandler()
        
        # Test transient error detection
        assert handler.is_transient_error(Exception("connection timeout"))
        assert not handler.is_transient_error(Exception("syntax error"))
        
        # Test disconnect error detection
        assert handler.is_disconnect_error(Exception("connection lost"))
        assert not handler.is_disconnect_error(Exception("syntax error"))

    def test_dialect_error_handling_integration(self):
        """Test error handling integration in dialect"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Test error handler methods
        assert callable(redshift_dialect.is_disconnect)
        assert hasattr(redshift_dialect.error_handler, 'is_transient_error')
        assert hasattr(redshift_dialect.error_handler, 'is_disconnect_error')
        
        # Test circuit breaker
        assert hasattr(redshift_dialect.circuit_breaker, 'state')
        assert redshift_dialect.circuit_breaker.state == 'CLOSED'

    def test_rollback_error_handling(self):
        """Test rollback error handling"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Should have enhanced rollback method
        assert hasattr(redshift_dialect, 'do_rollback')
        assert callable(redshift_dialect.do_rollback)

    def test_commit_error_handling(self):
        """Test commit error handling"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Should have enhanced commit method
        assert hasattr(redshift_dialect, 'do_commit')
        assert callable(redshift_dialect.do_commit)