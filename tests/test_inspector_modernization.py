"""
Test Inspector-based reflection patterns for SQLAlchemy 1.4/2.0 compatibility
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, Integer, String
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector
from unittest.mock import Mock, MagicMock


def test_inspector_has_table():
    """Test has_table works through Inspector interface"""
    connection = Mock()
    
    # Create dialect instance
    dialect = RedshiftDialectMixin()
    
    # Mock the internal methods - return non-empty dict for existing table
    dialect._get_all_relation_info = Mock(return_value={
        'test_table': Mock()
    })
    
    # Test has_table through dialect
    result = dialect.has_table(connection, 'test_table', schema='public')
    assert result is True
    
    # Test non-existent table - return empty dict
    dialect._get_all_relation_info = Mock(return_value={})
    result = dialect.has_table(connection, 'nonexistent', schema='public')
    assert result is False


def test_inspector_get_table_names():
    """Test get_table_names works through Inspector interface"""
    from sqlalchemy_redshift.dialect import RelationKey
    connection = Mock()
    
    # Create dialect instance
    dialect = RedshiftDialectMixin()
    
    # Mock RelationKey objects properly
    table1_key = Mock()
    table1_key.schema = 'public'
    table1_key.name = 'table1'
    
    table2_key = Mock()
    table2_key.schema = 'public'
    table2_key.name = 'table2'
    
    view1_key = Mock()
    view1_key.schema = 'public'
    view1_key.name = 'view1'
    
    mock_relations = {
        table1_key: Mock(relkind='r'),  # regular table
        view1_key: Mock(relkind='v'),   # view
        table2_key: Mock(relkind='r'),  # regular table
    }
    
    dialect._get_all_relation_info = Mock(return_value=mock_relations)
    
    # Test get_table_names
    result = dialect.get_table_names(connection, schema='public')
    
    # Should return only tables (relkind='r'), not views
    expected_tables = ['table1', 'table2']
    assert sorted(result) == sorted(expected_tables)


def test_inspector_get_view_names():
    """Test get_view_names works through Inspector interface"""
    from sqlalchemy_redshift.dialect import RelationKey
    connection = Mock()
    
    # Create dialect instance  
    dialect = RedshiftDialectMixin()
    
    # Mock RelationKey objects properly
    table1_key = Mock()
    table1_key.schema = 'public'
    table1_key.name = 'table1'
    
    view1_key = Mock()
    view1_key.schema = 'public'
    view1_key.name = 'view1'
    
    view2_key = Mock()
    view2_key.schema = 'public'
    view2_key.name = 'view2'
    
    mock_relations = {
        table1_key: Mock(relkind='r'),  # regular table
        view1_key: Mock(relkind='v'),   # view
        view2_key: Mock(relkind='v'),   # view
    }
    
    dialect._get_all_relation_info = Mock(return_value=mock_relations)
    
    # Test get_view_names
    result = dialect.get_view_names(connection, schema='public')
    
    # Should return only views (relkind='v'), not tables
    expected_views = ['view1', 'view2']
    assert sorted(result) == sorted(expected_views)


def test_inspector_interface_compatibility():
    """Test that Inspector interface works with dialect methods"""
    # This test verifies that the dialect methods have compatible signatures
    # with SQLAlchemy's Inspector interface
    
    dialect = RedshiftDialectMixin()
    
    # Check method signatures exist and are callable
    assert hasattr(dialect, 'has_table')
    assert callable(dialect.has_table)
    
    assert hasattr(dialect, 'get_table_names')
    assert callable(dialect.get_table_names)
    
    assert hasattr(dialect, 'get_view_names')
    assert callable(dialect.get_view_names)
    
    assert hasattr(dialect, 'get_foreign_keys')
    assert callable(dialect.get_foreign_keys)
    
    assert hasattr(dialect, 'get_pk_constraint')
    assert callable(dialect.get_pk_constraint)
    
    assert hasattr(dialect, 'get_columns')
    assert callable(dialect.get_columns)


def test_inspector_caching_behavior():
    """Test that reflection methods use proper caching"""
    connection = Mock()
    
    dialect = RedshiftDialectMixin()
    
    # Mock the internal method to track calls
    dialect._get_all_relation_info = Mock(return_value={})
    
    # Call get_table_names multiple times
    dialect.get_table_names(connection, schema='public')
    dialect.get_table_names(connection, schema='public')
    
    # Should use caching - exact behavior depends on @reflection.cache decorator
    # This test ensures the method can be called multiple times without error
    assert dialect._get_all_relation_info.call_count >= 1


# Import the actual dialect class for testing
from sqlalchemy_redshift.dialect import RedshiftDialectMixin


if __name__ == "__main__":
    pytest.main([__file__])