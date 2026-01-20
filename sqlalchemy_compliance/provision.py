"""Redshift-specific provisioning for SQLAlchemy test suite."""

from sqlalchemy import text
from sqlalchemy.testing import provision


@provision.temp_table_keyword_args.for_db("redshift")
def _redshift_temp_table_keyword_args(cfg, eng):
    return {"prefixes": ["TEMPORARY"]}


@provision.post_configure_engine.for_db("redshift")
def _redshift_post_configure_engine(url, engine, follower_ident):
    """Create test schemas needed by the test suite."""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema_2"))
        conn.commit()
