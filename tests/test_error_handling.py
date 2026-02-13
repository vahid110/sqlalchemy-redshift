"""Tests for production-grade error handling features"""
import pytest
from sqlalchemy_redshift.resilience import ProductionErrorHandler
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


class TestDisconnectDetection:
    """Test disconnect detection functionality"""
    
    @pytest.mark.parametrize("dialect_cls", [
        RedshiftDialect_redshift_connector
    ])
    def test_is_disconnect_method_exists(self, dialect_cls):
        """Ensure is_disconnect method exists for connection recycling"""
        dialect = dialect_cls()
        assert hasattr(dialect, 'is_disconnect'), f"Missing is_disconnect method for {dialect_cls}"
    
    def test_redshift_connector_has_do_ping(self):
        """Verify redshift_connector has do_ping for health checks"""
        dialect = RedshiftDialect_redshift_connector()
        assert hasattr(dialect, 'do_ping'), "Missing do_ping method for connection health checks"