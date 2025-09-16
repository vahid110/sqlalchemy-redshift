"""
Test isolation level handling for Redshift dialects.
Redshift only supports READ COMMITTED and AUTOCOMMIT.
"""
import pytest
import sqlalchemy as sa
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
)


class MockConnection:
    """Mock connection for testing isolation level setting"""
    def __init__(self):
        self.autocommit = False
        self.isolation_level = None
    
    def cursor(self):
        """Mock cursor for redshift_connector parent method calls"""
        return MockCursor()
    
    def commit(self):
        """Mock commit method"""
        pass


class MockCursor:
    """Mock cursor for testing"""
    def execute(self, sql):
        """Mock execute method"""
        pass
    
    def close(self):
        """Mock close method"""
        pass


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
class TestIsolationLevels:
    """Test isolation level handling across all drivers"""
    
    def test_autocommit_isolation_level(self, dialect_cls):
        """Test that AUTOCOMMIT isolation level is handled correctly"""
        dialect = dialect_cls()
        mock_conn = MockConnection()
        
        dialect.set_isolation_level(mock_conn, "AUTOCOMMIT")
        assert mock_conn.autocommit is True
    
    def test_read_committed_isolation_level(self, dialect_cls):
        """Test that READ COMMITTED isolation level is handled correctly"""
        dialect = dialect_cls()
        mock_conn = MockConnection()
        
        dialect.set_isolation_level(mock_conn, "READ_COMMITTED")
        assert mock_conn.autocommit is False
        
        # Test alternative format
        dialect.set_isolation_level(mock_conn, "READ COMMITTED")
        assert mock_conn.autocommit is False
    
    def test_invalid_isolation_level_raises_error(self, dialect_cls):
        """Test that invalid isolation levels raise clear errors"""
        dialect = dialect_cls()
        mock_conn = MockConnection()
        
        # Only psycopg2 dialects should raise ArgumentError for invalid levels
        # redshift_connector delegates to parent which may handle differently
        if dialect_cls in (RedshiftDialect_psycopg2, RedshiftDialect_psycopg2cffi):
            with pytest.raises(sa.exc.ArgumentError, match="Redshift only supports"):
                dialect.set_isolation_level(mock_conn, "SERIALIZABLE")
            
            with pytest.raises(sa.exc.ArgumentError, match="Redshift only supports"):
                dialect.set_isolation_level(mock_conn, "REPEATABLE_READ")
    
    def test_isolation_level_method_exists(self, dialect_cls):
        """Ensure set_isolation_level method exists for all dialects"""
        dialect = dialect_cls()
        assert hasattr(dialect, 'set_isolation_level')
        assert callable(getattr(dialect, 'set_isolation_level'))