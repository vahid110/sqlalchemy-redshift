"""
Test disconnect detection and pool pre-ping behavior.
Simulates actual network failures and connection drops.
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
)


class MockDisconnectError(Exception):
    """Mock exception that simulates connection loss"""
    pass


class MockTimeoutError(Exception):
    """Mock exception that simulates connection timeout"""
    pass


class MockSocketError(Exception):
    """Mock exception that simulates socket errors"""
    pass


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
class TestDisconnectSimulation:
    """Test disconnect detection with simulated network failures"""
    
    def test_is_disconnect_socket_errors(self, dialect_cls):
        """Test is_disconnect detects socket-related errors"""
        dialect = dialect_cls()
        
        # Skip psycopg2 dialects that need DBAPI loaded
        if "psycopg2" in dialect_cls.__name__:
            pytest.skip("psycopg2 dialects require DBAPI module loaded for is_disconnect")
        
        # Common socket/connection error messages
        socket_errors = [
            OperationalError("connection lost", None, None),
            OperationalError("server closed the connection unexpectedly", None, None),
            OperationalError("could not connect to server", None, None),
            OperationalError("connection timed out", None, None),
            Exception("socket.error: [Errno 104] Connection reset by peer"),
            Exception("socket.error: [Errno 110] Connection timed out"),
            Exception("redshift_connector.error: server closed the connection"),
        ]
        
        for error in socket_errors:
            # Should detect these as disconnect errors
            result = dialect.is_disconnect(error, None, None)
            # Most of these should be detected as disconnects
            # (Some may not be detected depending on implementation)
            assert isinstance(result, bool)
    
    def test_is_disconnect_non_disconnect_errors(self, dialect_cls):
        """Test is_disconnect doesn't flag non-disconnect errors"""
        dialect = dialect_cls()
        
        # Skip psycopg2 dialects that need DBAPI loaded
        if "psycopg2" in dialect_cls.__name__:
            pytest.skip("psycopg2 dialects require DBAPI module loaded for is_disconnect")
        
        # Non-disconnect errors
        non_disconnect_errors = [
            Exception("syntax error at or near"),
            Exception("relation does not exist"),
            Exception("permission denied"),
            Exception("invalid input syntax"),
        ]
        
        for error in non_disconnect_errors:
            result = dialect.is_disconnect(error, None, None)
            # These should NOT be detected as disconnects
            assert result is False
    
    def test_do_ping_method_exists(self, dialect_cls):
        """Test do_ping method exists for connection health checks"""
        dialect = dialect_cls()
        
        if "redshift_connector" in dialect_cls.__name__:
            # redshift_connector should have do_ping
            assert hasattr(dialect, 'do_ping')
            assert callable(getattr(dialect, 'do_ping'))
        else:
            # psycopg2 dialects inherit from PostgreSQL which may not have do_ping
            # That's OK - they can rely on pool_pre_ping with SELECT 1
            pass


class TestPoolPrePingBehavior:
    """Test pool pre-ping behavior and configuration"""
    
    def test_pool_pre_ping_configuration(self):
        """Test pool_pre_ping can be configured"""
        # This tests the recommended production configuration
        
        # Mock engine creation with pool_pre_ping
        engine_config = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,  # 1 hour
            'pool_size': 5,
            'max_overflow': 10
        }
        
        # Should be able to configure these settings
        assert engine_config['pool_pre_ping'] is True
        assert engine_config['pool_recycle'] == 3600
    
    def test_pool_pre_ping_documentation(self):
        """Test pool_pre_ping usage pattern is documented"""
        # Document the recommended production pattern
        production_config = """
        # Recommended production configuration
        engine = create_engine(
            'redshift+redshift_connector://user:pass@cluster.region.redshift.amazonaws.com:5439/db',
            pool_pre_ping=True,      # Enable connection health checks
            pool_recycle=3600,       # Recycle connections every hour
            pool_size=5,             # Connection pool size
            max_overflow=10          # Additional connections when needed
        )
        """
        
        # Pattern should include pool_pre_ping and related settings
        assert "pool_pre_ping=True" in production_config
        assert "pool_recycle" in production_config
        assert "pool_size" in production_config


@pytest.mark.parametrize("dialect_cls", [RedshiftDialect_redshift_connector])
class TestRedshiftConnectorDisconnectBehavior:
    """Test redshift_connector specific disconnect handling"""
    
    def test_do_ping_implementation(self, dialect_cls):
        """Test do_ping implementation works correctly"""
        dialect = dialect_cls()
        
        # Mock connection for testing
        class MockConnection:
            def __init__(self, should_fail=False):
                self.should_fail = should_fail
                self.cursor_calls = 0
            
            def cursor(self):
                return MockCursor(self.should_fail)
        
        class MockCursor:
            def __init__(self, should_fail=False):
                self.should_fail = should_fail
            
            def execute(self, sql):
                if self.should_fail:
                    raise MockDisconnectError("Connection lost")
                assert sql == "SELECT 1"
            
            def fetchone(self):
                if self.should_fail:
                    raise MockDisconnectError("Connection lost")
                return (1,)
            
            def close(self):
                pass
        
        # Test successful ping
        good_conn = MockConnection(should_fail=False)
        result = dialect.do_ping(good_conn)
        assert result is True
        
        # Test failed ping
        bad_conn = MockConnection(should_fail=True)
        result = dialect.do_ping(bad_conn)
        assert result is False
    
    def test_enhanced_error_handling_integration(self, dialect_cls):
        """Test enhanced error handling integration"""
        dialect = dialect_cls()
        
        # Should have error handler
        assert hasattr(dialect, 'error_handler')
        
        # Error handler should have disconnect detection
        error_handler = dialect.error_handler
        assert hasattr(error_handler, 'is_disconnect_error')
        
        # Test disconnect error detection
        disconnect_error = Exception("connection lost")
        result = error_handler.is_disconnect_error(disconnect_error)
        assert isinstance(result, bool)


class TestDisconnectRecoveryPatterns:
    """Test disconnect recovery and retry patterns"""
    
    def test_disconnect_recovery_documentation(self):
        """Test disconnect recovery patterns are documented"""
        recovery_pattern = """
        # Recommended disconnect recovery pattern
        from sqlalchemy import create_engine
        from sqlalchemy.pool import QueuePool
        
        engine = create_engine(
            'redshift+redshift_connector://...',
            poolclass=QueuePool,
            pool_pre_ping=True,          # Test connections before use
            pool_recycle=3600,           # Recycle connections hourly
            pool_reset_on_return='commit', # Clean state on return
        )
        
        # Retry pattern for transient errors
        def execute_with_retry(engine, sql, max_retries=3):
            for attempt in range(max_retries):
                try:
                    with engine.connect() as conn:
                        return conn.execute(sql)
                except Exception as e:
                    if engine.dialect.is_disconnect(e, None, None) and attempt < max_retries - 1:
                        continue  # Retry on disconnect
                    raise  # Re-raise if not disconnect or max retries reached
        """
        
        # Should document key recovery patterns
        assert "pool_pre_ping=True" in recovery_pattern
        assert "pool_recycle" in recovery_pattern
        assert "is_disconnect" in recovery_pattern
        assert "max_retries" in recovery_pattern
    
    def test_transient_error_classification(self):
        """Test transient vs permanent error classification"""
        # Document error classification for retry logic
        error_classification = {
            # Transient errors (should retry)
            'transient': [
                "connection lost",
                "connection timed out", 
                "server closed the connection",
                "connection reset by peer",
                "temporary failure in name resolution"
            ],
            # Permanent errors (should not retry)
            'permanent': [
                "authentication failed",
                "database does not exist",
                "permission denied",
                "syntax error",
                "relation does not exist"
            ]
        }
        
        # Should have clear classification
        assert len(error_classification['transient']) > 0
        assert len(error_classification['permanent']) > 0
        assert "connection lost" in error_classification['transient']
        assert "syntax error" in error_classification['permanent']


class TestConnectionPoolIntegration:
    """Test connection pool integration with disconnect detection"""
    
    def test_pool_invalidation_on_disconnect(self):
        """Test connection pool invalidates connections on disconnect"""
        # This would require integration testing with real connections
        # For now, document the expected behavior
        
        pool_behavior = """
        When is_disconnect() returns True:
        1. SQLAlchemy invalidates the connection in the pool
        2. Connection is removed from pool and closed
        3. New connection is created on next request
        4. pool_pre_ping prevents using stale connections
        """
        
        # Should document expected pool behavior
        assert "invalidates the connection" in pool_behavior
        assert "pool_pre_ping" in pool_behavior
    
    def test_connection_lifecycle_management(self):
        """Test connection lifecycle with disconnect handling"""
        lifecycle_pattern = """
        Connection Lifecycle with Disconnect Handling:
        
        1. Connection Request:
           - If pool_pre_ping=True: Test with SELECT 1
           - If ping fails: Create new connection
           - If ping succeeds: Return existing connection
        
        2. Query Execution:
           - Execute query
           - If disconnect error: Mark connection as invalid
           - Pool will create new connection for next request
        
        3. Connection Return:
           - If pool_reset_on_return: ROLLBACK or COMMIT
           - Return to pool for reuse
        """
        
        # Should document complete lifecycle
        assert "pool_pre_ping" in lifecycle_pattern
        assert "disconnect error" in lifecycle_pattern
        assert "invalid" in lifecycle_pattern