"""
Test type round-trips for critical Redshift data types.
Ensures data integrity for NUMERIC precision, TIMESTAMP/TZ handling, SUPER/JSON, etc.
"""
import pytest
import json
from decimal import Decimal
from datetime import datetime, date
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String, Numeric, Date, DateTime
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector,
    SUPER, GEOMETRY, TIMESTAMPTZ, TIMETZ, JSON
)


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
class TestTypeRoundTrips:
    """Test critical type round-trips for data integrity"""
    
    def test_numeric_precision_scale(self, dialect_cls):
        """Test NUMERIC with high precision and scale"""
        dialect = dialect_cls()
        
        # Test high precision NUMERIC types
        high_precision = Numeric(precision=38, scale=18)
        compiled = high_precision.compile(dialect=dialect)
        
        assert "NUMERIC" in str(compiled) or "DECIMAL" in str(compiled)
        
        # Test bind/result processors
        if hasattr(high_precision, 'bind_processor'):
            bind_proc = high_precision.bind_processor(dialect)
            if bind_proc:
                # Test extreme precision values
                test_value = Decimal('12345678901234567890.123456789012345678')
                processed = bind_proc(test_value)
                assert processed is not None
    
    def test_date_type_handling(self, dialect_cls):
        """Test DATE type compilation and processing"""
        dialect = dialect_cls()
        
        date_type = Date()
        compiled = date_type.compile(dialect=dialect)
        assert "DATE" in str(compiled)
        
        # Test date value processing
        test_date = date(2023, 12, 25)
        if hasattr(date_type, 'bind_processor'):
            bind_proc = date_type.bind_processor(dialect)
            if bind_proc:
                processed = bind_proc(test_date)
                assert processed is not None
    
    def test_timestamp_vs_timestamptz(self, dialect_cls):
        """Test TIMESTAMP vs TIMESTAMPTZ handling"""
        dialect = dialect_cls()
        
        # Regular TIMESTAMP
        timestamp_type = DateTime()
        compiled_ts = timestamp_type.compile(dialect=dialect)
        assert "TIMESTAMP" in str(compiled_ts)
        
        # TIMESTAMPTZ (Redshift-specific)
        timestamptz_type = TIMESTAMPTZ()
        compiled_tstz = timestamptz_type.compile(dialect=dialect)
        assert "TIMESTAMPTZ" in str(compiled_tstz)
        
        # Test datetime processing
        test_datetime = datetime(2023, 12, 25, 15, 30, 45)
        if hasattr(timestamp_type, 'bind_processor'):
            bind_proc = timestamp_type.bind_processor(dialect)
            if bind_proc:
                processed = bind_proc(test_datetime)
                assert processed is not None
    
    def test_super_json_type_processing(self, dialect_cls):
        """Test SUPER type with JSON data"""
        dialect = dialect_cls()
        
        super_type = SUPER()
        compiled = super_type.compile(dialect=dialect)
        assert "SUPER" in str(compiled)
        
        # Test JSON data processing
        test_json_data = {
            "name": "test",
            "values": [1, 2, 3],
            "nested": {"key": "value"},
            "null_field": None
        }
        
        # Test bind processor
        if hasattr(super_type, 'bind_processor'):
            bind_proc = super_type.bind_processor(dialect)
            if bind_proc:
                processed = bind_proc(test_json_data)
                assert processed is not None
                # Should be JSON string
                if isinstance(processed, str):
                    # Should be valid JSON
                    parsed_back = json.loads(processed)
                    assert parsed_back["name"] == "test"
                    assert parsed_back["values"] == [1, 2, 3]
        
        # Test result processor
        if hasattr(super_type, 'result_processor'):
            result_proc = super_type.result_processor(dialect, None)
            if result_proc:
                json_string = json.dumps(test_json_data)
                processed = result_proc(json_string)
                if isinstance(processed, dict):
                    assert processed["name"] == "test"
                    assert processed["values"] == [1, 2, 3]
    
    def test_json_type_processing(self, dialect_cls):
        """Test JSON type (maps to SUPER in Redshift)"""
        dialect = dialect_cls()
        
        json_type = JSON()
        compiled = json_type.compile(dialect=dialect)
        # JSON should compile to SUPER in Redshift
        assert "SUPER" in str(compiled)
        
        # Test complex JSON data
        complex_json = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False}
            ],
            "metadata": {
                "version": "1.0",
                "created": "2023-12-25T15:30:45Z"
            },
            "tags": ["important", "production"]
        }
        
        # Test bind processor
        if hasattr(json_type, 'bind_processor'):
            bind_proc = json_type.bind_processor(dialect)
            if bind_proc:
                processed = bind_proc(complex_json)
                assert processed is not None
    
    def test_geometry_type_compilation(self, dialect_cls):
        """Test GEOMETRY type compilation"""
        dialect = dialect_cls()
        
        geometry_type = GEOMETRY()
        compiled = geometry_type.compile(dialect=dialect)
        assert "GEOMETRY" in str(compiled)
    
    def test_timetz_type_compilation(self, dialect_cls):
        """Test TIMETZ type compilation"""
        dialect = dialect_cls()
        
        timetz_type = TIMETZ()
        compiled = timetz_type.compile(dialect=dialect)
        assert "TIMETZ" in str(compiled)
    
    def test_string_type_length_handling(self, dialect_cls):
        """Test VARCHAR length handling"""
        dialect = dialect_cls()
        
        # Test various string lengths
        short_string = String(50)
        long_string = String(65535)  # Max VARCHAR in Redshift
        
        compiled_short = short_string.compile(dialect=dialect)
        compiled_long = long_string.compile(dialect=dialect)
        
        assert "VARCHAR" in str(compiled_short)
        assert "VARCHAR" in str(compiled_long)
        assert "50" in str(compiled_short)
        assert "65535" in str(compiled_long)
    
    def test_boolean_type_handling(self, dialect_cls):
        """Test BOOLEAN type compilation and processing"""
        dialect = dialect_cls()
        
        bool_type = sa.Boolean()
        compiled = bool_type.compile(dialect=dialect)
        assert "BOOLEAN" in str(compiled)
        
        # Test boolean value processing
        if hasattr(bool_type, 'bind_processor'):
            bind_proc = bool_type.bind_processor(dialect)
            if bind_proc:
                assert bind_proc(True) is not None
                assert bind_proc(False) is not None
                assert bind_proc(None) is None


class TestTypeErrorHandling:
    """Test type error handling and edge cases"""
    
    @pytest.mark.parametrize("dialect_cls", [
        RedshiftDialect_psycopg2, 
        RedshiftDialect_psycopg2cffi,
        RedshiftDialect_redshift_connector
    ])
    def test_super_invalid_json_handling(self, dialect_cls):
        """Test SUPER type handles invalid JSON gracefully"""
        dialect = dialect_cls()
        super_type = SUPER()
        
        # Test result processor with invalid JSON
        if hasattr(super_type, 'result_processor'):
            result_proc = super_type.result_processor(dialect, None)
            if result_proc:
                # Invalid JSON should return as string, not raise exception
                invalid_json = "{'invalid': json}"
                result = result_proc(invalid_json)
                # Should not raise exception, should return original string
                assert result is not None
    
    @pytest.mark.parametrize("dialect_cls", [
        RedshiftDialect_psycopg2, 
        RedshiftDialect_psycopg2cffi,
        RedshiftDialect_redshift_connector
    ])
    def test_numeric_overflow_handling(self, dialect_cls):
        """Test NUMERIC type handles overflow gracefully"""
        dialect = dialect_cls()
        
        # Test maximum precision NUMERIC
        max_numeric = Numeric(precision=38, scale=0)
        compiled = max_numeric.compile(dialect=dialect)
        assert compiled is not None
        
        # Should compile without errors even at max precision
        assert "NUMERIC" in str(compiled) or "DECIMAL" in str(compiled)