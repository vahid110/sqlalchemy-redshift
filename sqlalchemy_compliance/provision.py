"""Redshift-specific provisioning for SQLAlchemy test suite."""

from sqlalchemy import text, inspect, event
from sqlalchemy.testing import provision
from sqlalchemy.schema import DropTable, DropConstraint
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.engine import Engine
import re


@provision.temp_table_keyword_args.for_db("redshift")
def _redshift_temp_table_keyword_args(cfg, eng):
    return {"prefixes": ["TEMPORARY"]}


def _strip_check_constraints(ddl_string):
    """Strip CHECK constraints from CREATE TABLE DDL.
    
    Redshift doesn't support CHECK constraints in CREATE TABLE syntax.
    This removes both named and unnamed CHECK constraints.
    Handles quoted identifiers with escaped quotes.
    """
    # Remove named CHECK constraints: CONSTRAINT "name with "" escaped quotes" CHECK (...)
    # The pattern (?:"(?:[^"]|"")*"|\w+) matches either:
    # - A quoted identifier with possible escaped quotes: "name""with""quotes"
    # - An unquoted identifier: name
    ddl_string = re.sub(
        r',\s*CONSTRAINT\s+(?:"(?:[^"]|"")*"|\w+)\s+CHECK\s*\([^)]*\)',
        '',
        ddl_string,
        flags=re.IGNORECASE
    )
    
    # Remove unnamed CHECK constraints: CHECK (...)
    ddl_string = re.sub(
        r',\s*CHECK\s*\([^)]*\)',
        '',
        ddl_string,
        flags=re.IGNORECASE
    )
    
    return ddl_string


# Register global event listener for ALL engines
@event.listens_for(Engine, "before_cursor_execute", retval=True)
def strip_check_from_all_engines(conn, cursor, statement, parameters, context, executemany):
    """Strip CHECK constraints and unsupported DDL from Redshift statements."""
    # Only apply to Redshift dialects
    if conn.dialect.name == 'redshift':
        if isinstance(statement, str):
            statement_upper = statement.upper()
            # Strip CHECK constraints from CREATE TABLE
            if 'CREATE TABLE' in statement_upper and 'CHECK' in statement_upper:
                statement = _strip_check_constraints(statement)
            # Skip COMMENT statements on CHECK constraints (they don't exist after stripping)
            elif 'COMMENT ON CONSTRAINT' in statement_upper:
                return "SELECT 1 WHERE FALSE", parameters
            # Skip CREATE INDEX (Redshift doesn't support indexes)
            elif statement_upper.strip().startswith('CREATE INDEX') or statement_upper.strip().startswith('CREATE UNIQUE INDEX'):
                return "SELECT 1 WHERE FALSE", parameters
            # Skip DROP INDEX
            elif statement_upper.strip().startswith('DROP INDEX'):
                return "SELECT 1 WHERE FALSE", parameters
    return statement, parameters


@provision.post_configure_engine.for_db("redshift")
def _redshift_post_configure_engine(url, engine, follower_ident):
    """Create test schemas and perform initial cleanup.
    
    This runs once at the start of the test session.
    We aggressively clean all schemas to prevent 'already exists' errors.
    """
    
    with engine.connect() as conn:
        # Create test schemas
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS test_schema_2"))
        
        # Perform aggressive cleanup of all test schemas
        inspector = inspect(conn)
        for schema in ['public', 'test_schema', 'test_schema_2']:
            # Drop all views first (may depend on tables)
            try:
                for view in inspector.get_view_names(schema=schema):
                    try:
                        if schema == 'public':
                            conn.execute(text(f'DROP VIEW IF EXISTS "{view}" CASCADE'))
                        else:
                            conn.execute(text(f'DROP VIEW IF EXISTS "{schema}"."{view}" CASCADE'))
                    except Exception:
                        pass
            except Exception:
                pass
            
            # Drop all tables
            try:
                for table in inspector.get_table_names(schema=schema):
                    try:
                        if schema == 'public':
                            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                        else:
                            conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}" CASCADE'))
                    except Exception:
                        pass
            except Exception:
                pass
        
        conn.commit()


@provision.drop_all_schema_objects_pre_tables.for_db("redshift")
def _redshift_drop_all_schema_objects_pre_tables(cfg, eng, inspector, schema, tables, **kw):
    """Drop views before tables since views may depend on tables.
    
    This is called by SQLAlchemy's test framework before dropping tables.
    We aggressively drop all views and tables to prevent 'already exists' errors.
    """
    with eng.begin() as conn:
        # Get all schemas to clean (handle None schema as public)
        schemas_to_clean = [schema] if schema else ['public', 'test_schema', 'test_schema_2']
        
        for schema_name in schemas_to_clean:
            # Drop all views first
            try:
                view_names = inspector.get_view_names(schema=schema_name)
                for view_name in view_names:
                    try:
                        if schema_name and schema_name != 'public':
                            conn.execute(text(f'DROP VIEW IF EXISTS "{schema_name}"."{view_name}" CASCADE'))
                        else:
                            conn.execute(text(f'DROP VIEW IF EXISTS "{view_name}" CASCADE'))
                    except Exception:
                        pass  # Ignore errors, continue cleanup
            except Exception:
                pass
            
            # Drop all tables (in case some weren't tracked by SQLAlchemy)
            try:
                table_names = inspector.get_table_names(schema=schema_name)
                for table_name in table_names:
                    try:
                        if schema_name and schema_name != 'public':
                            conn.execute(text(f'DROP TABLE IF EXISTS "{schema_name}"."{table_name}" CASCADE'))
                        else:
                            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                    except Exception:
                        pass  # Ignore errors, continue cleanup
            except Exception:
                pass


@provision.drop_all_schema_objects_post_tables.for_db("redshift")
def _redshift_drop_all_schema_objects_post_tables(cfg, eng, inspector, schema, tables, **kw):
    """Additional cleanup after tables are dropped."""
    # Redshift doesn't have sequences or other objects that need post-table cleanup
    pass
