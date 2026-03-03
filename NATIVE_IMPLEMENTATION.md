# Native redshift_connector Implementation Plan

**Branch:** `sa2_rsconn_native`  
**Strategy:** Fresh start from main, use redshift_connector's native APIs

---

## Goal

Add `redshift+redshift_connector://` dialect that:
- Uses redshift_connector's native `cursor.get_*()` methods for reflection
- Supports SQLAlchemy 2.0
- Maintains backward compatibility (psycopg2 unchanged)

---

## Reference Implementation Strategy

**sqlalchemy2 branch is our reference** - it contains:
- All SA 2.0 compatibility flags discovered through testing
- Multi-reflection method implementation patterns
- Compliance test results - what works, what doesn't
- Bug fixes for SA 2.0 edge cases

**Implementation approach:**
1. **Structure from sqlalchemy2 branch** - Flags, method signatures, SA 2.0 patterns
2. **Implementation from redshift_connector** - Use `cursor.get_columns()`, etc. instead of custom SQL
3. **Tests from sqlalchemy2 branch** - Cherry-pick all compliance tests

---

## Implementation Steps

### Step 1: Rename existing class for backward compatibility
```python
# Rename existing
class RedshiftDialect_redshift_connector_legacy(RedshiftDialectMixin, PGDialect):
    # ... existing code unchanged
```

### Step 2: Create new RedshiftDialect_redshift_connector from scratch
```python
class RedshiftDialect_redshift_connector(RedshiftDialectMixin, PGDialect):
    """SA 2.0 compatible, uses redshift_connector native APIs"""
    supports_statement_cache = True
    driver = 'redshift_connector'
    
    def get_columns(self, connection, table_name, schema=None, **kw):
        cursor = connection.connection.cursor()
        result = cursor.get_columns(catalog=..., schema_pattern=..., tablename_pattern=...)
        return self._convert_to_sa_format(result)
```

### Step 3: Add SA 2.0 multi-reflection methods
- `get_multi_columns()` - Use `cursor.get_columns()` for all tables
- `get_multi_pk_constraint()` - Use `cursor.get_primary_keys()`
- `get_multi_foreign_keys()` - Use `cursor.get_imported_keys()`
- `get_multi_unique_constraints()` - Return empty (Redshift doesn't enforce)
- `get_multi_indexes()` - Return empty (Redshift doesn't support)

### Step 4: Update setup.py
```python
'redshift.redshift_connector = ...RedshiftDialect_redshift_connector',  # New
'redshift.redshift_connector_legacy = ...RedshiftDialect_redshift_connector_legacy',  # Old
```

### Step 5: Test
- Run existing unit tests
- Cherry-pick compliance tests from sqlalchemy2 branch
- Verify psycopg2 still works
- Verify legacy redshift_connector still works

---

## Key Decisions

1. **Rename existing class** - `RedshiftDialect_redshift_connector_legacy` for backward compatibility
2. **New class from scratch** - Clean implementation using native APIs
3. **Use redshift_connector natively** - `cursor.get_columns()`, `cursor.get_primary_keys()`, etc.
4. **Keep psycopg2 unchanged** - Backward compatible
5. **Reuse tests** - Cherry-pick from sqlalchemy2 branch
6. **Simple architecture** - No complex strategy patterns

---

## Timeline

- **Step 1**: Rename existing class (5 min)
- **Step 2**: Create new class skeleton (30 min)
- **Step 3**: Implement reflection methods (2 hours)
- **Step 4**: Add SA 2.0 multi-methods (1 hour)
- **Step 5**: Test and fix (2 hours)

**Total: ~6 hours**

---

## Success Criteria

- ✅ `redshift+redshift_connector://` uses new implementation
- ⏳ `redshift+redshift_connector_legacy://` uses old implementation (needs setup.py)
- ✅ Reflection uses `cursor.get_*()` native APIs (with SQL fallback)
- ✅ SA 2.0 compatible
- ✅ psycopg2 unchanged
- ⏳ Tests pass (need to add tests)
- ✅ Backward compatible

---

## Progress

### ✅ Step 1: Rename existing class (DONE)
- Renamed `RedshiftDialect_redshift_connector` → `RedshiftDialect_redshift_connector_legacy`
- Added backward compatibility docstring
- Commit: daa834f

### ✅ Step 2-3: Implement new class with native APIs (DONE)
- `get_columns()` - Uses `cursor.get_columns()` with SQL fallback
- `get_table_names()` - Uses `cursor.get_tables(types=['TABLE'])`
- `get_view_names()` - Uses `cursor.get_tables(types=['VIEW'])`
- `get_pk_constraint()` - Uses `cursor.get_primary_keys()` with SQL fallback
- `get_foreign_keys()` - Uses `cursor.get_imported_keys()` with SQL fallback
- `get_multi_columns()` - SA 2.0 multi-reflection
- `get_multi_pk_constraint()` - SA 2.0 multi-reflection
- `get_multi_foreign_keys()` - SA 2.0 multi-reflection
- `get_multi_unique_constraints()` - Returns empty dict
- `get_multi_indexes()` - Returns empty dict
- Commit: dfe500d

**Tested on:**
- Cluster v1.0.117891 (show_discovery v2) - SQL fallback works ✅
- Cluster v1.0.227967 (show_discovery v4+) - Native APIs work ✅

### ⏳ Step 4: Update setup.py (TODO)
- Add entry point for new dialect
- Add entry point for legacy dialect

### ⏳ Step 5: Add tests (TODO)

**Test Categories from sqlalchemy2 branch:**

1. **Unit Tests** (no cluster needed):
   - `test_sqlalchemy2_compatibility.py` - SA 2.0 flags and methods
   - `test_dialect_types.py` - Type system tests
   - `test_compiler.py` - SQL compilation tests

2. **Integration Tests** (require cluster):
   - `test_reflection.py` - Reflection methods (PRIORITY)
   - `test_inspector_modernization.py` - SA 2.0 Inspector features
   - `test_real_cluster_smoke.py` - Basic connectivity

3. **Compliance Tests** (sqlalchemy_compliance/):
   - SQLAlchemy test suite integration
   - setup.cfg with connection string

**Implementation Plan:**
- Add basic unit test for native API paths
- Cherry-pick reflection tests from sqlalchemy2
- Add test for show_discovery fallback behavior
