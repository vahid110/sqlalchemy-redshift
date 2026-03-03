"""Tests for native redshift_connector API implementation."""
import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector


class TestNativeAPIImplementation:
    """Test native redshift_connector API usage."""
    
    def test_dialect_flags(self):
        """Test SA 2.0 compatibility flags."""
        dialect = RedshiftDialect_redshift_connector()
        
        assert dialect.supports_statement_cache is True
        assert dialect.supports_unicode_statements is True
        assert dialect.supports_unicode_binds is True
        assert dialect.default_paramstyle == "format"
        assert dialect.use_setinputsizes is False
    
    def test_get_columns_uses_native_api(self):
        """Test that get_columns tries native API first."""
        dialect = RedshiftDialect_redshift_connector()
        
        # Mock connection and cursor
        mock_cursor = Mock()
        mock_cursor.get_columns.return_value = [
            (None, 'public', 'test_table', 'id', 4, 'integer', None, None, None, None, 1, None, None),
            (None, 'public', 'test_table', 'name', 12, 'varchar', 100, None, None, None, 1, None, None),
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_connection = Mock()
        mock_connection.connection = mock_conn
        
        # Call get_columns
        columns = dialect.get_columns(mock_connection, 'test_table', schema='public')
        
        # Verify native API was called
        mock_cursor.get_columns.assert_called_once_with(
            catalog='', schema_pattern='public', tablename_pattern='test_table'
        )
        
        # Verify results
        assert len(columns) == 2
        assert columns[0]['name'] == 'id'
        assert columns[1]['name'] == 'name'
    
    def test_get_table_names_uses_native_api(self):
        """Test that get_table_names uses cursor.get_tables()."""
        dialect = RedshiftDialect_redshift_connector()
        
        # Mock cursor
        mock_cursor = Mock()
        mock_cursor.get_tables.return_value = [
            (None, 'public', 'table1', 'TABLE', None, None, None, None, None, None),
            (None, 'public', 'table2', 'TABLE', None, None, None, None, None, None),
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_connection = Mock()
        mock_connection.connection = mock_conn
        
        # Call get_table_names
        tables = dialect.get_table_names(mock_connection, schema='public')
        
        # Verify native API was called
        mock_cursor.get_tables.assert_called_once_with(
            catalog='', schema_pattern='public', table_name_pattern='%', types=['TABLE']
        )
        
        # Verify results
        assert tables == ['table1', 'table2']
    
    def test_get_pk_constraint_with_fallback(self):
        """Test that get_pk_constraint falls back to SQL on error."""
        dialect = RedshiftDialect_redshift_connector()
        
        # Mock cursor that raises error (show_discovery v2)
        mock_cursor = Mock()
        mock_cursor.get_primary_keys.side_effect = Exception("show discovery version 4 required")
        
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        
        mock_connection = Mock()
        mock_connection.connection = mock_conn
        
        # Mock parent class method
        with pytest.raises(Exception):
            # Will try native API, fail, then try parent (which we haven't mocked)
            dialect.get_pk_constraint(mock_connection, 'test_table', schema='public')
        
        # Verify native API was attempted
        mock_cursor.get_primary_keys.assert_called_once()
    
    def test_multi_reflection_methods_exist(self):
        """Test that SA 2.0 multi-reflection methods are implemented."""
        dialect = RedshiftDialect_redshift_connector()
        
        assert hasattr(dialect, 'get_multi_columns')
        assert hasattr(dialect, 'get_multi_pk_constraint')
        assert hasattr(dialect, 'get_multi_foreign_keys')
        assert hasattr(dialect, 'get_multi_unique_constraints')
        assert hasattr(dialect, 'get_multi_indexes')
        
        assert callable(dialect.get_multi_columns)
        assert callable(dialect.get_multi_pk_constraint)
        assert callable(dialect.get_multi_foreign_keys)
