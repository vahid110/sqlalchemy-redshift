# Deprecation Notice: psycopg2/psycopg2cffi Dialects

## Summary

The `psycopg2` and `psycopg2cffi` dialects have **limited SQLAlchemy 2.0 support** and are maintained for backward compatibility only. We strongly recommend migrating to the `redshift_connector` dialect for new projects.

## Why Deprecate?

### Root Cause
The psycopg2-based dialects inherit from SQLAlchemy's PostgreSQL dialect, which assumes PostgreSQL 9.1+ features. Redshift is based on PostgreSQL 8.0.2 and lacks many modern PostgreSQL system columns.

### Specific Issues with SQLAlchemy 2.0

1. **Reflection Failures**: PostgreSQL dialect queries `pg_attribute.attcollation` and other columns that don't exist in Redshift
2. **Incompatible System Queries**: Many PostgreSQL introspection queries fail on Redshift
3. **Maintenance Burden**: Requires overriding numerous PostgreSQL methods to work around incompatibilities

## Migration Path

### Before (psycopg2)
```python
import sqlalchemy as sa

engine = sa.create_engine(
    'redshift+psycopg2://user:pass@host:5439/db'
)
```

### After (redshift_connector - Recommended)
```python
import sqlalchemy as sa

engine = sa.create_engine(
    'redshift+redshift_connector://user:pass@host:5439/db'
)
```

## What Still Works

The psycopg2 dialects still support:
- ✅ Basic queries and DML operations
- ✅ DDL compilation (CREATE TABLE, etc.)
- ✅ COPY and UNLOAD commands
- ✅ Isolation level management (AUTOCOMMIT, READ COMMITTED)
- ✅ Connection pooling

## What Doesn't Work (SA 2.0)

- ❌ Table reflection (get_columns, get_pk_constraint, etc.)
- ❌ View reflection
- ❌ External table reflection
- ❌ Some constraint introspection

## Test Status

### Passing Tests
- **192/192 parametrized tests** (all dialects including psycopg2)
- **14/14 cluster integration tests**

### Skipped Tests (psycopg2 only)
- **~57 reflection tests** - Skip when using psycopg2 dialects
- **~45 legacy SA 1.4 syntax tests** - Use old `sa.select([col])` syntax
- **~12 materialized view tests** - Feature not yet implemented

## Deprecation Timeline

- **Current (v0.9.x)**: psycopg2 dialects emit DeprecationWarning on initialization
- **Future (v1.0.0)**: psycopg2 dialects may be removed or marked as unsupported

## Recommendation

**Use `redshift_connector` dialect for:**
- All new projects
- SQLAlchemy 2.0+ applications
- Applications requiring reflection/introspection
- Production deployments

**Continue using psycopg2 only if:**
- You have existing code that can't be migrated immediately
- You don't use reflection features
- You understand the limitations

## Questions?

See README.rst for detailed usage examples and migration guidance.
