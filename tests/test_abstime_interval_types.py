"""
Tests for ABSTIME and INTERVAL data types
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer
from sqlalchemy.engine import create_mock_engine

from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector
from sqlalchemy_redshift import dialect


class TestAbstimeType:
    """Test ABSTIME data type"""
    
    def test_abstime_type_available(self):
        """Test that ABSTIME type is available"""
        assert hasattr(dialect, 'ABSTIME')

    def test_abstime_type_properties(self):
        """Test ABSTIME type properties"""
        abstime_type = dialect.ABSTIME()
        assert abstime_type.__visit_name__ == "ABSTIME"

    def test_abstime_type_compilation(self):
        """Test ABSTIME type compilation"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        
        abstime_type = dialect.ABSTIME()
        assert type_compiler.visit_ABSTIME(abstime_type) == "ABSTIME"

    def test_abstime_in_ischema_names(self):
        """Test that ABSTIME is registered in ischema_names"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        ischema_names = redshift_dialect.ischema_names
        
        assert 'abstime' in ischema_names
        assert ischema_names['abstime'] == dialect.ABSTIME

    def test_abstime_ddl_generation(self):
        """Test ABSTIME in DDL generation"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'abstime_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('abs_time_col', dialect.ABSTIME()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'ABSTIME' in ddl


class TestIntervalType:
    """Test INTERVAL data type"""
    
    def test_interval_type_available(self):
        """Test that INTERVAL type is available"""
        assert hasattr(dialect, 'INTERVAL')

    def test_interval_type_properties(self):
        """Test INTERVAL type properties"""
        interval_type = dialect.INTERVAL()
        assert interval_type.__visit_name__ == "INTERVAL"

    def test_interval_type_compilation(self):
        """Test INTERVAL type compilation"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        
        interval_type = dialect.INTERVAL()
        assert type_compiler.visit_INTERVAL(interval_type) == "INTERVAL"

    def test_interval_in_ischema_names(self):
        """Test that INTERVAL is registered in ischema_names"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        ischema_names = redshift_dialect.ischema_names
        
        assert 'interval' in ischema_names
        assert ischema_names['interval'] == dialect.INTERVAL

    def test_interval_ddl_generation(self):
        """Test INTERVAL in DDL generation"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'interval_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('interval_col', dialect.INTERVAL()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'INTERVAL' in ddl


class TestAbstimeIntervalIntegration:
    """Test ABSTIME and INTERVAL types together"""
    
    def test_both_types_in_same_table(self):
        """Test using both ABSTIME and INTERVAL in the same table"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'time_types_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('created_at', dialect.ABSTIME()),
            Column('duration', dialect.INTERVAL()),
        )
        
        ddl = str(sa.schema.CreateTable(table).compile(engine))
        assert 'ABSTIME' in ddl
        assert 'INTERVAL' in ddl
        assert len(table.columns) == 3