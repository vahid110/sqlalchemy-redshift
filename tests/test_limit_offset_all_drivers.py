import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, select
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
)
import pytest


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
def test_offset_only_requires_limit_all_all_drivers(dialect_cls):
    """Test that OFFSET-only queries add LIMIT ALL for all drivers"""
    meta = MetaData()
    t = Table("t", meta, Column("id", Integer))
    stmt = select(t.c.id).offset(10)
    compiled = stmt.compile(dialect=dialect_cls())
    s = str(compiled)
    assert "OFFSET" in s and "LIMIT ALL" in s


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
def test_limit_with_offset_no_limit_all(dialect_cls):
    """Test that LIMIT+OFFSET queries don't add extra LIMIT ALL"""
    meta = MetaData()
    t = Table("t", meta, Column("id", Integer))
    stmt = select(t.c.id).limit(5).offset(10)
    compiled = stmt.compile(dialect=dialect_cls())
    s = str(compiled)
    # Check for LIMIT and OFFSET keywords (values are parameterized)
    assert "LIMIT" in s and "OFFSET" in s
    # Should not have LIMIT ALL when LIMIT is already present
    assert "LIMIT ALL" not in s