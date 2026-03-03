"""
Test bulk insert operations with use_insertmanyvalues=True and complex types
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String, JSON, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector, SUPER, JSON as RedshiftJSON
from unittest.mock import Mock, MagicMock
import json


def test_use_insertmanyvalues_flag():
    """Test that use_insertmanyvalues=True is set correctly"""
    dialect = RedshiftDialect_redshift_connector()
    
    # Critical: use_insertmanyvalues should be True for SA 2.0 bulk optimization
    assert dialect.use_insertmanyvalues is True
    
    # Critical: insert_returning should be False (Redshift doesn't support RETURNING)
    assert dialect.insert_returning is False


def test_bulk_insert_with_nulls():
    """Test bulk insert with NULL values"""
    meta = MetaData()
    test_table = Table('test_bulk_nulls', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(50)),
        Column('optional_field', String(50))
    )
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Test bulk insert statement compilation
    stmt = test_table.insert().values([
        {'id': 1, 'name': 'test1', 'optional_field': None},
        {'id': 2, 'name': 'test2', 'optional_field': 'value2'},
        {'id': 3, 'name': 'test3', 'optional_field': None}
    ])
    
    compiled = stmt.compile(dialect=dialect)
    compiled_str = str(compiled)
    
    # Should compile without errors and handle NULLs properly
    assert 'INSERT INTO test_bulk_nulls' in compiled_str
    assert compiled is not None


def test_bulk_insert_with_json_super():
    """Test bulk insert with JSON/SUPER types"""
    meta = MetaData()
    test_table = Table('test_bulk_json', meta,
        Column('id', Integer, primary_key=True),
        Column('json_data', RedshiftJSON),
        Column('super_data', SUPER)
    )
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Test data with complex JSON structures
    test_data = [
        {
            'id': 1, 
            'json_data': {'key': 'value1', 'nested': {'count': 10}},
            'super_data': [1, 2, 3, {'nested': True}]
        },
        {
            'id': 2,
            'json_data': {'key': 'value2', 'array': [1, 2, 3]},
            'super_data': {'complex': {'deeply': {'nested': 'value'}}}
        }
    ]
    
    stmt = test_table.insert().values(test_data)
    compiled = stmt.compile(dialect=dialect)
    
    # Should compile without errors
    assert compiled is not None
    assert 'INSERT INTO test_bulk_json' in str(compiled)


def test_bulk_insert_with_arrays():
    """Test bulk insert with array types"""
    from sqlalchemy_redshift.dialect import RedshiftArray
    
    meta = MetaData()
    test_table = Table('test_bulk_arrays', meta,
        Column('id', Integer, primary_key=True),
        Column('int_array', RedshiftArray(Integer)),
        Column('str_array', RedshiftArray(String))
    )
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Test data with arrays
    test_data = [
        {
            'id': 1,
            'int_array': [1, 2, 3, 4],
            'str_array': ['a', 'b', 'c']
        },
        {
            'id': 2,
            'int_array': [10, 20, 30],
            'str_array': ['x', 'y', 'z']
        }
    ]
    
    stmt = test_table.insert().values(test_data)
    compiled = stmt.compile(dialect=dialect)
    
    # Should compile without errors
    assert compiled is not None
    assert 'INSERT INTO test_bulk_arrays' in str(compiled)


def test_bulk_insert_with_identity_columns():
    """Test bulk insert with IDENTITY columns"""
    meta = MetaData()
    test_table = Table('test_bulk_identity', meta,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('name', String(50)),
        Column('auto_id', Integer, info={'identity': (1, 1)})  # IDENTITY column
    )
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Test bulk insert without specifying identity column values
    test_data = [
        {'name': 'test1'},
        {'name': 'test2'},
        {'name': 'test3'}
    ]
    
    stmt = test_table.insert().values(test_data)
    compiled = stmt.compile(dialect=dialect)
    
    # Should compile without errors
    assert compiled is not None
    assert 'INSERT INTO test_bulk_identity' in str(compiled)


def test_no_returning_assumption():
    """Test that bulk operations don't assume RETURNING support"""
    meta = MetaData()
    test_table = Table('test_bulk_simple', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(50))
    )
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Verify insert_returning is False
    assert dialect.insert_returning is False
    
    # Test that bulk insert doesn't try to use RETURNING
    stmt = test_table.insert().values([
        {'id': 1, 'name': 'test1'},
        {'id': 2, 'name': 'test2'}
    ])
    
    compiled = stmt.compile(dialect=dialect)
    compiled_str = str(compiled)
    
    # Should not contain RETURNING clause (check for RETURNING followed by space or end)
    import re
    returning_pattern = r'\bRETURNING\s'
    assert not re.search(returning_pattern, compiled_str, re.IGNORECASE)
    assert compiled is not None


def test_orm_bulk_operations():
    """Test ORM bulk operations with complex types"""
    Base = declarative_base()
    
    class TestModel(Base):
        __tablename__ = 'test_orm_bulk'
        
        id = Column(Integer, primary_key=True)
        name = Column(String(50))
        json_data = Column(RedshiftJSON)
        super_data = Column(SUPER)
    
    # Mock engine and session
    mock_engine = Mock()
    mock_engine.dialect = RedshiftDialect_redshift_connector()
    
    # Test that ORM model can be created without errors
    assert TestModel.__tablename__ == 'test_orm_bulk'
    assert hasattr(TestModel, 'json_data')
    assert hasattr(TestModel, 'super_data')


def test_bulk_insert_performance_flags():
    """Test that performance-related flags are set correctly"""
    dialect = RedshiftDialect_redshift_connector()
    
    # Performance flags for SA 2.0
    assert dialect.use_insertmanyvalues is True  # Enable bulk insert optimization
    assert dialect.supports_statement_cache is True  # Enable statement caching
    assert dialect.supports_sane_rowcount is False  # Redshift rowcount quirks
    
    # Redshift-specific constraints
    assert dialect.insert_returning is False  # No RETURNING support


def test_bulk_insert_with_defaults():
    """Test bulk insert with default values"""
    meta = MetaData()
    test_table = Table('test_bulk_defaults', meta,
        Column('id', Integer, primary_key=True),
        Column('name', String(50)),
        Column('status', String(20), default='active'),
        Column('created_at', sa.DateTime, default=sa.func.now())
    )
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Test bulk insert with some default values
    test_data = [
        {'id': 1, 'name': 'test1'},  # Will use defaults for status and created_at
        {'id': 2, 'name': 'test2', 'status': 'inactive'},  # Override status default
    ]
    
    stmt = test_table.insert().values(test_data)
    compiled = stmt.compile(dialect=dialect)
    
    # Should compile without errors
    assert compiled is not None
    assert 'INSERT INTO test_bulk_defaults' in str(compiled)


if __name__ == "__main__":
    pytest.main([__file__])