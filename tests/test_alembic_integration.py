"""Test Alembic integration with SQLAlchemy 2.0"""
import pytest

try:
    import alembic
    from alembic.runtime.migration import MigrationContext
    from alembic.operations import Operations
    ALEMBIC_AVAILABLE = True
except ImportError:
    ALEMBIC_AVAILABLE = False

from sqlalchemy import create_mock_engine, Column, Integer, String
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector


@pytest.mark.skipif(not ALEMBIC_AVAILABLE, reason="Alembic not available")
def test_alembic_migration_context():
    """Test Alembic migration context with Redshift dialect"""
    
    def dump(sql, *multiparams, **params):
        # Collect SQL statements for verification
        dump.statements.append(str(sql))
    
    dump.statements = []
    
    # Create mock engine with Redshift dialect
    engine = create_mock_engine("redshift+redshift_connector://test", dump)
    
    # Test migration context creation
    conn = engine.connect()
    context = MigrationContext.configure(conn)
    ops = Operations(context)
    
    # Test basic DDL operations
    ops.create_table('test_table',
        Column('id', Integer, primary_key=True),
        Column('name', String(50))
    )
    
    # Verify SQL was generated
    assert len(dump.statements) > 0
    assert 'CREATE TABLE test_table' in dump.statements[0]


@pytest.mark.skipif(not ALEMBIC_AVAILABLE, reason="Alembic not available")
def test_alembic_redshift_ddl_compilation():
    """Test that Alembic can compile DDL with Redshift dialect"""
    
    def dump(sql, *multiparams, **params):
        dump.statements.append(str(sql))
    
    dump.statements = []
    
    # Create mock engine
    engine = create_mock_engine("redshift+redshift_connector://test", dump)
    
    conn = engine.connect()
    context = MigrationContext.configure(conn)
    ops = Operations(context)
    
    # Test basic table operations that should work with Redshift
    ops.create_table('redshift_table',
        Column('id', Integer, primary_key=True),
        Column('data', String(100))
    )
    
    ops.add_column('redshift_table', Column('email', String(255)))
    ops.drop_column('redshift_table', 'email')
    ops.drop_table('redshift_table')
    
    # Verify DDL was generated and uses Redshift dialect
    assert len(dump.statements) >= 4  # CREATE, ADD, DROP, DROP
    
    create_sql = dump.statements[0]
    assert 'CREATE TABLE redshift_table' in create_sql
    assert 'INTEGER' in create_sql  # Redshift type
    assert 'VARCHAR' in create_sql  # Redshift type


@pytest.mark.skipif(not ALEMBIC_AVAILABLE, reason="Alembic not available") 
def test_alembic_version_compatibility():
    """Test Alembic version compatibility with SQLAlchemy 2.0"""
    
    # Verify Alembic can import and work with our dialect
    from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector
    
    dialect = RedshiftDialect_redshift_connector()
    assert dialect is not None
    
    # Test that dialect works with Alembic's expected interface
    assert hasattr(dialect, 'name')
    assert dialect.name == 'redshift'
    
    # Test that Alembic can create migration context with our dialect
    engine = create_mock_engine("redshift+redshift_connector://test", lambda *a, **k: None)
    conn = engine.connect()
    context = MigrationContext.configure(conn)
    assert context.dialect.name == 'redshift'