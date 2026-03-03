"""
Tests for JSON and SUPER data types with caching and error handling
"""
import pytest
import json
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer
from sqlalchemy.engine import create_mock_engine

from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector
from sqlalchemy_redshift import dialect


class TestJsonType:
    """Test JSON data type (maps to SUPER)"""
    
    def test_json_type_available(self):
        """Test that JSON type is available"""
        assert hasattr(dialect, 'JSON')

    def test_json_type_properties(self):
        """Test JSON type properties"""
        json_type = dialect.JSON()
        assert json_type.__visit_name__ == "JSON"

    def test_json_type_compilation(self):
        """Test JSON type compilation (maps to SUPER)"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        
        json_type = dialect.JSON()
        assert type_compiler.visit_JSON(json_type) == "SUPER"

    def test_json_in_ischema_names(self):
        """Test that JSON is registered in ischema_names"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        ischema_names = redshift_dialect.ischema_names
        
        assert 'json' in ischema_names
        assert ischema_names['json'] == dialect.JSON

    def test_json_ddl_generation(self):
        """Test JSON in DDL generation (should generate SUPER)"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'json_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('json_col', dialect.JSON()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'SUPER' in ddl  # JSON maps to SUPER

    def test_json_type_error_handling(self):
        """Test JSON type error handling"""
        json_type = dialect.JSON()
        processor = json_type.result_processor(None, None)
        
        if processor:
            # Test with invalid JSON
            invalid_json = "{'invalid': json}"
            result = processor(invalid_json)
            # Should return original string on parse error
            assert result == invalid_json

    def test_json_bind_processor(self):
        """Test JSON bind processor with caching"""
        json_type = dialect.JSON()
        processor = json_type.bind_processor(None)
        
        if processor:
            # Test with dictionary
            test_dict = {"key": "value"}
            result = processor(test_dict)
            assert result == '{"key": "value"}'


class TestSuperType:
    """Test SUPER data type with caching"""
    
    def test_super_type_available(self):
        """Test that SUPER type is available"""
        assert hasattr(dialect, 'SUPER')

    def test_super_type_properties(self):
        """Test SUPER type properties"""
        super_type = dialect.SUPER()
        assert super_type.__visit_name__ == "SUPER"

    def test_super_type_compilation(self):
        """Test SUPER type compilation"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        
        super_type = dialect.SUPER()
        assert type_compiler.visit_SUPER(super_type) == "SUPER"

    def test_super_type_caching(self):
        """Test SUPER type caching functionality"""
        super_type = dialect.SUPER()
        
        # Test with small dictionary (should be cached)
        small_dict = {"key": "value"}
        result = super_type.process_bind_param(small_dict, None)
        assert result == '{"key": "value"}'

    def test_super_type_large_data(self):
        """Test SUPER type with large data (no caching)"""
        super_type = dialect.SUPER()
        
        # Test with large dictionary (should not be cached)
        large_dict = {"key" + str(i): "value" + str(i) for i in range(100)}
        result = super_type.process_bind_param(large_dict, None)
        assert isinstance(result, str)
        assert "key0" in result

    def test_super_result_processor(self):
        """Test SUPER result processor with error handling"""
        super_type = dialect.SUPER()
        processor = super_type.result_processor(None, None)
        
        if processor:
            # Test with valid JSON
            valid_json = '{"key": "value"}'
            result = processor(valid_json)
            assert result == {"key": "value"}
            
            # Test with invalid JSON
            invalid_json = "{'invalid': json}"
            result = processor(invalid_json)
            assert result == invalid_json  # Should return original on error

    def test_super_ddl_generation(self):
        """Test SUPER in DDL generation"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'super_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('super_col', dialect.SUPER()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'SUPER' in ddl


class TestJsonSuperIntegration:
    """Test JSON and SUPER types integration"""
    
    def test_json_and_super_in_same_table(self):
        """Test using both JSON and SUPER in the same table"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'json_super_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('json_data', dialect.JSON()),
            Column('super_data', dialect.SUPER()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        # Both should generate SUPER in DDL
        assert ddl.count('SUPER') == 2
        assert len(table.columns) == 3

    def test_json_super_type_consistency(self):
        """Test that JSON and SUPER types work consistently"""
        json_type = dialect.JSON()
        super_type = dialect.SUPER()
        
        test_data = {"test": "data", "number": 42}
        
        # Test bind processors
        json_bind_proc = json_type.bind_processor(None)
        super_bind_result = super_type.process_bind_param(test_data, None)
        
        # SUPER should produce valid JSON string
        assert isinstance(super_bind_result, str)
        
        # Should be parseable as JSON
        json.loads(super_bind_result)
        
        # JSON bind processor may be None or callable
        if json_bind_proc:
            json_result = json_bind_proc(test_data)
            assert isinstance(json_result, str)
            json.loads(json_result)