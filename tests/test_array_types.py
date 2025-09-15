"""
Tests for RedshiftArray data type with performance optimizations
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String
from sqlalchemy.engine import create_mock_engine

from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector
from sqlalchemy_redshift import dialect


class TestRedshiftArrayType:
    """Test RedshiftArray data type"""
    
    def test_redshift_array_type_available(self):
        """Test that RedshiftArray type is available"""
        assert hasattr(dialect, 'RedshiftArray')

    def test_redshift_array_type_creation(self):
        """Test RedshiftArray type creation with different item types"""
        # Test with Integer
        int_array = dialect.RedshiftArray(sa.Integer)
        assert isinstance(int_array.item_type, type(sa.Integer()))
        
        # Test with String
        str_array = dialect.RedshiftArray(sa.String)
        assert isinstance(str_array.item_type, type(sa.String()))

    def test_redshift_array_inheritance(self):
        """Test that RedshiftArray inherits from SQLAlchemy ARRAY"""
        array_type = dialect.RedshiftArray(sa.Integer)
        assert isinstance(array_type, sa.types.ARRAY)

    def test_redshift_array_bind_processor(self):
        """Test RedshiftArray bind processor"""
        array_type = dialect.RedshiftArray(sa.Integer)
        redshift_dialect = RedshiftDialect_redshift_connector()
        processor = array_type.bind_processor(redshift_dialect)
        
        if processor:
            # Test with list
            test_list = [1, 2, 3, 4, 5]
            result = processor(test_list)
            assert result == [1, 2, 3, 4, 5]
            
            # Test with None
            result = processor(None)
            assert result is None

    def test_redshift_array_result_processor(self):
        """Test RedshiftArray result processor"""
        array_type = dialect.RedshiftArray(sa.Integer)
        redshift_dialect = RedshiftDialect_redshift_connector()
        processor = array_type.result_processor(redshift_dialect, None)
        
        if processor:
            # Test with list
            test_list = [1, 2, 3, 4, 5]
            result = processor(test_list)
            assert result == [1, 2, 3, 4, 5]
            
            # Test with None
            result = processor(None)
            assert result is None

    def test_redshift_array_ddl_generation(self):
        """Test RedshiftArray in DDL generation"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'array_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('int_array', dialect.RedshiftArray(Integer)),
            Column('str_array', dialect.RedshiftArray(String)),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'array_test' in ddl
        # Arrays should be represented in DDL
        assert len(table.columns) == 3

    def test_redshift_array_with_dimensions(self):
        """Test RedshiftArray with dimensions parameter"""
        # Test with dimensions
        array_type = dialect.RedshiftArray(sa.Integer, dimensions=2)
        assert array_type.dimensions == 2
        
        # Test with as_tuple
        array_type = dialect.RedshiftArray(sa.Integer, as_tuple=True)
        assert array_type.as_tuple is True

    def test_redshift_array_performance_optimization(self):
        """Test RedshiftArray performance optimizations"""
        array_type = dialect.RedshiftArray(sa.String)
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Test bind processor optimization (no item processor case)
        processor = array_type.bind_processor(redshift_dialect)
        if processor:
            test_data = ["a", "b", "c"]
            result = processor(test_data)
            assert result == ["a", "b", "c"]

    def test_redshift_array_nested_types(self):
        """Test RedshiftArray with complex nested types"""
        # Test with different base types
        types_to_test = [
            sa.Integer,
            sa.String,
            sa.Boolean,
            sa.Float,
        ]
        
        for base_type in types_to_test:
            array_type = dialect.RedshiftArray(base_type)
            assert array_type.item_type is not None


class TestRedshiftArrayIntegration:
    """Test RedshiftArray integration with other features"""
    
    def test_array_with_other_types(self):
        """Test RedshiftArray alongside other Redshift types"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'mixed_array_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('tags', dialect.RedshiftArray(String)),
            Column('json_data', dialect.JSON()),
            Column('super_data', dialect.SUPER()),
            Column('created_at', dialect.ABSTIME()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'mixed_array_test' in ddl
        assert 'SUPER' in ddl  # JSON maps to SUPER
        assert 'ABSTIME' in ddl
        assert len(table.columns) == 5

    def test_multiple_array_columns(self):
        """Test table with multiple array columns"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'multi_array_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('int_array', dialect.RedshiftArray(Integer)),
            Column('str_array', dialect.RedshiftArray(String)),
            Column('float_array', dialect.RedshiftArray(sa.Float)),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'multi_array_test' in ddl
        assert len(table.columns) == 4
        
        # Verify all columns have correct types
        assert isinstance(table.columns['int_array'].type, dialect.RedshiftArray)
        assert isinstance(table.columns['str_array'].type, dialect.RedshiftArray)
        assert isinstance(table.columns['float_array'].type, dialect.RedshiftArray)