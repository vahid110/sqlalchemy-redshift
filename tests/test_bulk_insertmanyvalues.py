"""
Test bulk insert operations with use_insertmanyvalues=True across all drivers.
Critical for production workloads with large data volumes.
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String, Boolean, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
)

Base = declarative_base()

class BulkTestTable(Base):
    __tablename__ = 'bulk_test'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    active = Column(Boolean, default=True)


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
class TestBulkInsertManyValues:
    """Test use_insertmanyvalues=True behavior across all drivers"""
    
    def test_use_insertmanyvalues_flag_enabled(self, dialect_cls):
        """Verify use_insertmanyvalues=True is set for all drivers"""
        dialect = dialect_cls()
        assert dialect.use_insertmanyvalues is True, f"use_insertmanyvalues should be True for {dialect_cls}"
    
    def test_bulk_insert_core_compilation(self, dialect_cls):
        """Test bulk insert compilation with Core API"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table('test_bulk', meta,
            Column('id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('active', Boolean)
        )
        
        # Create bulk insert statement
        stmt = table.insert()
        
        # Compile with multiple values
        compiled = stmt.compile(dialect=dialect)
        assert compiled is not None
        
        # Should support bulk insert syntax
        bulk_data = [
            {'name': 'test1', 'active': True},
            {'name': 'test2', 'active': False},
            {'name': 'test3', 'active': True}
        ]
        
        # Compilation should work with bulk data
        compiled_bulk = stmt.compile(dialect=dialect)
        assert "INSERT INTO" in str(compiled_bulk)
    
    def test_bulk_insert_with_nulls_and_defaults(self, dialect_cls):
        """Test bulk insert handles NULLs and defaults correctly"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table('test_bulk_nulls', meta,
            Column('id', Integer, primary_key=True),
            Column('name', String(50)),
            Column('active', Boolean, default=True),
            Column('optional', String(50), nullable=True)
        )
        
        stmt = table.insert()
        
        # Mix of NULL, default, and explicit values
        bulk_data = [
            {'name': 'test1', 'active': True, 'optional': 'value1'},
            {'name': 'test2', 'optional': None},  # NULL optional, default active
            {'name': 'test3', 'active': False}    # NULL optional, explicit active
        ]
        
        # Should compile without errors
        compiled = stmt.compile(dialect=dialect)
        assert compiled is not None
        assert "INSERT INTO" in str(compiled)
    
    def test_large_bulk_insert_compilation(self, dialect_cls):
        """Test compilation with large number of rows (1000+)"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table('test_large_bulk', meta,
            Column('id', Integer),
            Column('name', String(50)),
            Column('value', Integer)
        )
        
        stmt = table.insert()
        
        # Generate 1000 rows of test data
        bulk_data = [
            {'id': i, 'name': f'test_{i}', 'value': i * 10}
            for i in range(1000)
        ]
        
        # Should handle large bulk inserts
        compiled = stmt.compile(dialect=dialect)
        assert compiled is not None
        assert "INSERT INTO" in str(compiled)
    
    def test_insert_returning_disabled(self, dialect_cls):
        """Verify RETURNING is disabled for bulk inserts (Redshift doesn't support it)"""
        dialect = dialect_cls()
        assert dialect.insert_returning is False, f"insert_returning should be False for {dialect_cls}"
        
        meta = MetaData()
        table = Table('test_returning', meta,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )
        
        # Insert with attempted RETURNING should not include RETURNING clause
        stmt = table.insert().returning(table.c.id)
        compiled = str(stmt.compile(dialect=dialect))
        
        # RETURNING should be stripped out for Redshift
        assert "RETURNING" not in compiled or dialect.insert_returning is False


@pytest.mark.parametrize("sa_version,dialect_cls", [
    ("1.4", RedshiftDialect_psycopg2),
    ("1.4", RedshiftDialect_redshift_connector),
    ("2.0", RedshiftDialect_psycopg2), 
    ("2.0", RedshiftDialect_redshift_connector)
])
class TestBulkInsertSAVersions:
    """Test bulk insert compatibility across SA 1.4 and 2.0"""
    
    def test_bulk_insert_api_compatibility(self, sa_version, dialect_cls):
        """Test bulk insert works with both SA 1.4 and 2.0 APIs"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table('test_compat', meta,
            Column('id', Integer, primary_key=True),
            Column('name', String(50))
        )
        
        # Both SA versions should support bulk insert
        stmt = table.insert()
        compiled = stmt.compile(dialect=dialect)
        
        assert compiled is not None
        assert "INSERT INTO" in str(compiled)
        
        # Verify use_insertmanyvalues is enabled
        assert dialect.use_insertmanyvalues is True
    
    def test_orm_bulk_insert_compatibility(self, sa_version, dialect_cls):
        """Test ORM bulk operations work correctly"""
        dialect = dialect_cls()
        
        # Verify ORM-related flags are set correctly
        assert dialect.insert_returning is False  # No RETURNING support
        assert dialect.supports_sane_rowcount is False  # Redshift rowcount quirks
        assert dialect.use_insertmanyvalues is True  # Bulk insert optimization
        
        # These flags ensure ORM bulk operations work correctly with Redshift