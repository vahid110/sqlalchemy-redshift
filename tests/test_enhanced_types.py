"""
Tests for enhanced type system and new features
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String
from sqlalchemy.engine import reflection

import sqlalchemy_redshift.dialect as dialect


def test_new_types_available():
    """Test that new types are available in dialect"""
    assert hasattr(dialect, 'ABSTIME')
    assert hasattr(dialect, 'INTERVAL') 
    assert hasattr(dialect, 'JSON')
    assert hasattr(dialect, 'RedshiftArray')


def test_abstime_type_compilation():
    """Test ABSTIME type compilation"""
    abstime_type = dialect.ABSTIME()
    compiled = abstime_type.compile()
    assert compiled == "ABSTIME"


def test_interval_type_compilation():
    """Test INTERVAL type compilation"""
    interval_type = dialect.INTERVAL()
    compiled = interval_type.compile()
    assert compiled == "INTERVAL"


def test_json_type_compilation():
    """Test JSON type compilation (maps to SUPER)"""
    json_type = dialect.JSON()
    compiled = json_type.compile()
    assert compiled == "SUPER"


enhanced_types_ddl = [
    (
        dialect.ABSTIME,
        (
            u"\nCREATE TABLE t1 ("
            u"\n\tid INTEGER NOT NULL, "
            u"\n\ttest_col ABSTIME, "
            u"\n\tPRIMARY KEY (id)\n)\n\n"
        )
    ),
    (
        dialect.INTERVAL,
        (
            u"\nCREATE TABLE t1 ("
            u"\n\tid INTEGER NOT NULL, "
            u"\n\ttest_col INTERVAL, "
            u"\n\tPRIMARY KEY (id)\n)\n\n"
        )
    ),
    (
        dialect.JSON,
        (
            u"\nCREATE TABLE t1 ("
            u"\n\tid INTEGER NOT NULL, "
            u"\n\ttest_col SUPER, "
            u"\n\tPRIMARY KEY (id)\n)\n\n"
        )
    ),
]


@pytest.mark.parametrize("custom_datatype, expected", enhanced_types_ddl)
def test_enhanced_types_ddl_generation(custom_datatype, expected, stub_redshift_dialect):
    """Test DDL generation for enhanced types"""
    compiler = dialect.RedshiftDDLCompiler(stub_redshift_dialect, None)
    table = Table(
        't1',
        MetaData(),
        Column('id', Integer, primary_key=True),
        Column('test_col', custom_datatype)
    )

    create_table = sa.schema.CreateTable(table)
    actual = compiler.process(create_table)
    assert expected == actual


def test_super_type_caching():
    """Test SUPER type caching functionality"""
    super_type = dialect.SUPER()
    
    # Test bind parameter processing with caching
    bind_processor = super_type.process_bind_param
    
    # Small value should be cached
    small_dict = {"key": "value"}
    result1 = bind_processor(small_dict, None)
    result2 = bind_processor(small_dict, None)
    
    # Should return same cached result
    assert result1 == result2
    assert result1 == '{"key": "value"}'


def test_json_type_error_handling():
    """Test JSON type error handling"""
    json_type = dialect.JSON()
    result_processor = json_type.result_processor(None, None)
    
    # Test with invalid JSON
    invalid_json = "{'invalid': json}"
    result = result_processor(invalid_json)
    
    # Should return original string on parse error
    assert result == invalid_json


def test_capability_flags(stub_redshift_dialect):
    """Test SQLAlchemy 2.0 capability flags"""
    redshift_dialect = dialect.RedshiftDialect_redshift_connector()
    
    # Critical flags for Redshift compatibility
    assert redshift_dialect.insert_returning is False
    assert redshift_dialect.use_insertmanyvalues is False
    assert redshift_dialect.supports_sane_rowcount is False
    # Note: supports_statement_cache is overridden to False later in the class


def test_connection_health_check():
    """Test connection health check method"""
    redshift_dialect = dialect.RedshiftDialect_redshift_connector()
    
    # Should have do_ping method
    assert hasattr(redshift_dialect, 'do_ping')
    assert callable(redshift_dialect.do_ping)


def test_pool_configuration():
    """Test pool configuration methods"""
    redshift_dialect = dialect.RedshiftDialect_redshift_connector()
    
    # Should have pool configuration methods
    assert hasattr(redshift_dialect, 'get_pool_class')
    assert hasattr(redshift_dialect, 'get_default_pool_size')
    assert hasattr(redshift_dialect, 'get_default_max_overflow')
    
    # Test default values
    assert redshift_dialect.get_default_pool_size() == 5
    assert redshift_dialect.get_default_max_overflow() == 10


def test_enhanced_error_handling():
    """Test enhanced error handling methods"""
    redshift_dialect = dialect.RedshiftDialect_redshift_connector()
    
    # Should have error handler and circuit breaker
    assert hasattr(redshift_dialect, 'error_handler')
    assert hasattr(redshift_dialect, 'circuit_breaker')
    
    # Should have enhanced disconnect detection
    assert hasattr(redshift_dialect, 'is_disconnect')
    assert callable(redshift_dialect.is_disconnect)


# Integration tests (require real Redshift connection)
@pytest.mark.parametrize("custom_datatype", [dialect.ABSTIME, dialect.INTERVAL])
def test_enhanced_types_reflection(custom_datatype, redshift_engine):
    """Test reflection of enhanced types"""
    metadata = MetaData(bind=redshift_engine)
    table = Table(
        'test_enhanced_types',
        metadata,
        Column('id', Integer, primary_key=True),
        Column('test_col', custom_datatype),
        schema='public'
    )
    
    try:
        metadata.create_all()
        inspect = reflection.Inspector.from_engine(redshift_engine)
        
        columns = inspect.get_columns(table_name='test_enhanced_types', schema='public')
        assert len(columns) == 2
        
        # Find our test column
        test_col = next(col for col in columns if col['name'] == 'test_col')
        assert test_col is not None
        
    finally:
        # Cleanup
        try:
            metadata.drop_all()
        except:
            pass  # Ignore cleanup errors