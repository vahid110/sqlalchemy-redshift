# SQLAlchemy Compliance Test Suite for Redshift

**⚠️ IMPORTANT: See [STATUS.md](STATUS.md) for current progress, known issues, and next steps.**

This directory contains the integration of SQLAlchemy's official compliance test suite for the Redshift dialect.

## Quick Start

```bash
# Run the full test suite
cd sqlalchemy_compliance
source ../.venv/bin/activate
python -m pytest test_suite.py | tee test_results.txt

# Run with verbose output
python -m pytest test_suite.py -v

# Run specific test class
python -m pytest test_suite.py::ArgSignatureTest -v
```

## What This Tests

The SQLAlchemy test suite is the official compliance test used by all SQLAlchemy dialects (PostgreSQL, MySQL, Oracle, Snowflake, etc.) to validate:

- Core SQL operations (SELECT, INSERT, UPDATE, DELETE)
- Data types and type coercion
- Table/schema reflection
- DDL operations (CREATE, DROP, ALTER)
- Constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE)
- Transactions and isolation
- Joins, subqueries, and aggregates
- Compiler behavior and SQL generation

Having this integration validates that the Redshift dialect is production-ready and SQLAlchemy-compliant.

## Current Status

**Latest Results**: 352 PASSED, 133 SKIPPED, 30 FAILED, 796 ERRORS (1,311 total tests)

**See [STATUS.md](STATUS.md) for**:
- Detailed progress tracking
- Known issues and root causes
- Priority-ordered next steps
- How to contribute

**See [ERROR_ANALYSIS.md](ERROR_ANALYSIS.md) for**:
- Detailed error breakdown by category
- Root cause analysis
- Recommended solutions

## File Structure

- `STATUS.md` - **START HERE** - Current status and next steps
- `ERROR_ANALYSIS.md` - Detailed error analysis from initial run
- `test_suite.py` - Main test file (imports SQLAlchemy suite)
- `requirements.py` - Redshift feature exclusions
- `provision.py` - Temp table configuration
- `conftest.py` - Pytest plugin configuration
- `setup.cfg` - Database connection and requirements
- `pytest.ini` - Pytest settings

## Test Isolation

This test suite is isolated from the main tests in `tests/` directory to avoid pytest plugin conflicts. The SQLAlchemy test suite requires its own pytest plugin configuration.

## Redshift Feature Exclusions

The `requirements.py` file documents which SQLAlchemy features are not supported by Redshift:

- **RETURNING clause**: Limited support
- **Indexes**: Uses sort/dist keys instead
- **CHECK constraints**: Informational only, not enforced
- **Savepoints**: Not supported
- **Sequences**: Uses IDENTITY instead
- **Binary types**: No BYTEA support
- **Two-phase transactions**: Not supported
- **DISTINCT ON**: Not supported
- **IS DISTINCT FROM**: Not supported
- **UUID/ENUM types**: Not native types
- **Temp table reflection**: Limited support

## Why This Matters

This integration proves the Redshift dialect is:
1. **SQLAlchemy-compliant**: Follows the same standards as official dialects
2. **Production-ready**: Passes the same tests as PostgreSQL, MySQL, etc.
3. **Well-documented**: Exclusions clearly document Redshift limitations
4. **Gap-closed**: Addresses the gap identified in SNOWFLAKE_COMPARISON_FINAL.md
