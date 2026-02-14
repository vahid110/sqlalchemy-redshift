"""Redshift-specific provisioning for SQLAlchemy test suite."""

from sqlalchemy import text, inspect
from sqlalchemy.testing import provision
from sqlalchemy.schema import DropTable, DropConstraint
from sqlalchemy.exc import ProgrammingError


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


@provision.drop_all_schema_objects_pre_tables.for_db("redshift")
def _redshift_drop_all_schema_objects_pre_tables(cfg, eng, inspector, schema, tables, **kw):
    """Drop views before tables since views may depend on tables."""
    with eng.begin() as conn:
        # Drop all views in the schema - be aggressive
        try:
            for view_name in inspector.get_view_names(schema=schema):
                try:
                    conn.execute(text(f'DROP VIEW IF EXISTS "{schema}"."{view_name}" CASCADE'))
                except Exception:
                    pass
        except Exception:
            pass
        
        # Also drop views in public schema if schema is None
        if schema is None or schema == 'public':
            try:
                for view_name in inspector.get_view_names(schema='public'):
                    try:
                        conn.execute(text(f'DROP VIEW IF EXISTS "{view_name}" CASCADE'))
                    except Exception:
                        pass
            except Exception:
                pass


@provision.drop_all_schema_objects_post_tables.for_db("redshift")
def _redshift_drop_all_schema_objects_post_tables(cfg, eng, inspector, schema, tables, **kw):
    """Additional cleanup after tables are dropped."""
    # Redshift doesn't have sequences or other objects that need post-table cleanup
    pass
