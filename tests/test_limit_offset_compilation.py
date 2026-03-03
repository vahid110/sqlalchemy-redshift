"""
Test LIMIT/OFFSET compilation with SQLAlchemy 1.4/2.0 compatibility
"""
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, select
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector


def test_limit_offset_compilation():
    """Test that LIMIT/OFFSET compiles correctly with both SA 1.4 and 2.0"""
    meta = MetaData()
    test_table = Table('test_table', meta, Column('id', Integer), Column('name', sa.String))
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Test LIMIT only
    stmt1 = select(test_table.c.id).limit(10)
    compiled1 = stmt1.compile(dialect=dialect)
    assert "LIMIT" in str(compiled1)
    
    # Test OFFSET only (should add LIMIT ALL)
    stmt2 = select(test_table.c.id).offset(5)
    compiled2 = stmt2.compile(dialect=dialect)
    assert "LIMIT ALL" in str(compiled2)
    assert "OFFSET" in str(compiled2)
    
    # Test LIMIT and OFFSET
    stmt3 = select(test_table.c.id).limit(10).offset(5)
    compiled3 = stmt3.compile(dialect=dialect)
    assert "LIMIT" in str(compiled3)
    assert "OFFSET" in str(compiled3)
    assert "LIMIT ALL" not in str(compiled3)  # Should not have LIMIT ALL when LIMIT is present


def test_limit_offset_with_cte():
    """Test LIMIT/OFFSET with CTEs (Common Table Expressions)"""
    meta = MetaData()
    test_table = Table('test_table', meta, Column('id', Integer), Column('name', sa.String))
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Create a CTE with LIMIT/OFFSET
    cte = select(test_table.c.id).limit(100).cte('limited_data')
    stmt = select(cte.c.id).limit(10).offset(5)
    
    compiled = stmt.compile(dialect=dialect)
    compiled_str = str(compiled)
    
    # Should compile without errors
    assert "LIMIT" in compiled_str
    assert "OFFSET" in compiled_str


def test_limit_offset_with_subquery():
    """Test LIMIT/OFFSET with subqueries"""
    meta = MetaData()
    test_table = Table('test_table', meta, Column('id', Integer), Column('name', sa.String))
    
    dialect = RedshiftDialect_redshift_connector()
    
    # Create a subquery with LIMIT
    subq = select(test_table.c.id).limit(50).subquery()
    stmt = select(subq.c.id).limit(10)
    
    compiled = stmt.compile(dialect=dialect)
    compiled_str = str(compiled)
    
    # Should compile without errors
    assert "LIMIT" in compiled_str