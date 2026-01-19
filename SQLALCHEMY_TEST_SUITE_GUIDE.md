# SQLAlchemy Test Suite Integration Guide

## Overview

SQLAlchemy provides an official compliance test suite (`sqlalchemy.testing.suite`) that all dialect implementations should pass. This ensures compatibility and correctness across different database backends.

## What is the Test Suite?

The SQLAlchemy test suite includes comprehensive tests for:

- **Core SQL Operations**: SELECT, INSERT, UPDATE, DELETE
- **DDL Operations**: CREATE TABLE, DROP TABLE, indexes, constraints
- **Type System**: All SQL types (INTEGER, VARCHAR, TIMESTAMP, etc.)
- **Reflection**: Introspecting database schema (tables, columns, indexes, FKs)
- **Transactions**: COMMIT, ROLLBACK, isolation levels
- **Result Handling**: Fetching rows, cursor behavior
- **Edge Cases**: NULL handling, unicode, special characters

## Implementation Status

### ✅ Completed
- Created `tests/test_suite.py` that imports SQLAlchemy's test suite
- Tests will run automatically with `pytest tests/test_suite.py`

### 🔄 Next Steps

1. **Run the suite and identify failures**:
   ```bash
   pytest tests/test_suite.py -v --tb=short > suite_results.txt 2>&1
   ```

2. **Categorize failures**:
   - **Redshift limitations** (skip these tests)
   - **Missing dialect features** (implement these)
   - **Bugs** (fix these)

3. **Configure test exclusions** in `tests/test_suite.py`:
   ```python
   from sqlalchemy.testing import exclusions
   
   # Skip tests for unsupported features
   __backend_requirements__ = exclusions.closed()
   
   # Example: Skip ALTER COLUMN tests
   __requires__ = exclusions.skip_if(
       lambda config: True,
       "Redshift doesn't support ALTER COLUMN"
   )
   ```

4. **Implement missing features** identified by test failures

## Known Redshift Limitations

These features should be excluded from the test suite:

### DDL Limitations
- ❌ `ALTER COLUMN` (change type, set NOT NULL)
- ❌ `CHECK` constraints (not enforced)
- ❌ `FOREIGN KEY` enforcement (metadata only)
- ❌ User-defined domains
- ❌ Sequences (use IDENTITY instead)

### PostgreSQL Version
- Redshift is based on PostgreSQL 8.0.2 (2005)
- Missing features from modern PostgreSQL:
  - `pg_collation` (added in PG 9.1)
  - `ORDER BY` in aggregate functions
  - Many system catalog improvements

### Type System
- ✅ Most standard SQL types supported
- ⚠️ SUPER type (Redshift-specific JSON)
- ⚠️ GEOMETRY/GEOGRAPHY types

## Example: Configuring Test Exclusions

```python
# tests/test_suite.py

from sqlalchemy.testing.suite import *
from sqlalchemy.testing import exclusions, config

# Exclude ALTER COLUMN tests
class AlterTableTest:
    __skip_if__ = exclusions.skip_if(
        lambda: True,
        "Redshift doesn't support ALTER COLUMN"
    )

# Exclude CHECK constraint enforcement tests  
class CheckConstraintTest:
    __skip_if__ = exclusions.skip_if(
        lambda: True,
        "Redshift CHECK constraints are metadata-only"
    )

# Exclude FK enforcement tests
class ForeignKeyTest:
    __skip_if__ = exclusions.skip_if(
        lambda: True,
        "Redshift FK constraints are metadata-only"
    )
```

## Running the Suite

### Run all compliance tests:
```bash
pytest tests/test_suite.py -v
```

### Run specific test class:
```bash
pytest tests/test_suite.py::ComponentReflectionTest -v
```

### Run with detailed output:
```bash
pytest tests/test_suite.py -v --tb=short -x
```

### Save results for analysis:
```bash
pytest tests/test_suite.py -v --tb=short > suite_results.txt 2>&1
```

## Benefits

1. **Compatibility**: Ensures sqlalchemy-redshift works like other dialects
2. **Regression Prevention**: Catches breaking changes early
3. **Documentation**: Tests serve as usage examples
4. **Confidence**: Comprehensive validation of all features

## References

- [SQLAlchemy Testing Documentation](https://docs.sqlalchemy.org/en/20/core/testing.html)
- [Dialect Testing Guide](https://github.com/sqlalchemy/sqlalchemy/blob/main/README.dialects.rst)
- [Test Suite Source](https://github.com/sqlalchemy/sqlalchemy/tree/main/lib/sqlalchemy/testing/suite)

## Current Status

**File Created**: `tests/test_suite.py`
**Next Action**: Run the suite and analyze results to configure exclusions
**Expected Outcome**: Most tests should pass; exclude only Redshift-specific limitations
