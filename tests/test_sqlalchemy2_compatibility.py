"""
Tests for SQLAlchemy 2.0 compatibility features
"""
import pytest
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector


class TestSQLAlchemy2Compatibility:
    """Test SQLAlchemy 2.0 compatibility flags and features"""
    
    def test_capability_flags(self):
        """Test SQLAlchemy 2.0 capability flags"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Critical flags for Redshift compatibility
        assert redshift_dialect.insert_returning is False
        assert redshift_dialect.use_insertmanyvalues is True
        assert redshift_dialect.supports_sane_rowcount is False

    def test_connection_methods(self):
        """Test connection-related methods"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Should have connection health check
        assert hasattr(redshift_dialect, 'do_ping')
        assert callable(redshift_dialect.do_ping)

    def test_pool_configuration(self):
        """Test pool configuration methods"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Should have pool configuration methods
        assert hasattr(redshift_dialect, 'get_pool_class')
        assert hasattr(redshift_dialect, 'get_default_pool_size')
        assert hasattr(redshift_dialect, 'get_default_max_overflow')
        
        # Test default values
        assert redshift_dialect.get_default_pool_size() == 5
        assert redshift_dialect.get_default_max_overflow() == 10

    def test_error_handling_components(self):
        """Test error handling components are available"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Should have error handler
        assert hasattr(redshift_dialect, 'error_handler')
        
        # Should have enhanced disconnect detection
        assert hasattr(redshift_dialect, 'is_disconnect')
        assert callable(redshift_dialect.is_disconnect)

    def test_dialect_registration(self):
        """Test that dialect is properly registered and can be used"""
        # Test dialect registration
        from sqlalchemy.dialects import registry
        
        # Our dialect should be available
        dialect_cls = registry.load('redshift.redshift_connector')
        assert dialect_cls is not None
        assert issubclass(dialect_cls, RedshiftDialect_redshift_connector)

    def test_all_required_methods_present(self):
        """Test that all required dialect methods are present"""
        dialect_instance = RedshiftDialect_redshift_connector()
        
        required_methods = [
            'create_connect_args',
            'do_ping',
            'is_disconnect',
            'get_pool_class',
            'get_default_pool_size',
            'get_default_max_overflow'
        ]
        
        for method_name in required_methods:
            assert hasattr(dialect_instance, method_name), f"Missing method: {method_name}"
            assert callable(getattr(dialect_instance, method_name)), f"Method not callable: {method_name}"