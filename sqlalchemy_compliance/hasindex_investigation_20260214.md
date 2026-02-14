# HasIndexTest Investigation & Fix
**Date**: 2026-02-14
**Status**: ✅ COMPLETE - 4/4 tests now skipped

## Problem
All 4 HasIndexTest tests were failing:
- test_has_index[dialect]
- test_has_index[inspector]
- test_has_index_schema[dialect]
- test_has_index_schema[inspector]

**Error**: `AssertionError: assert False` - `has_index()` returns False when tests expect True

## Root Cause Analysis

### What the Tests Do
1. Create a table with columns
2. Create an Index: `Index("my_idx", table.c.data)`
3. Call `has_index("test_table", "my_idx")`
4. Expect: True (index exists)
5. Actual: False (index doesn't exist)

### Why It Fails
**Redshift doesn't support traditional indexes.**

Our dialect correctly handles this:
- `supports_indexes = False` in dialect
- `indexes = False` in requirements.py
- DDL compiler returns `"SELECT 1 WHERE FALSE"` for CREATE INDEX (no-op)

When tests create an Index object:
1. SQLAlchemy calls our DDL compiler
2. We return no-op SQL
3. No index actually gets created in Redshift
4. `has_index()` correctly returns False
5. Tests fail because they expect True

### The Mismatch
Tests assume: "If I create an Index object, the index exists"
Reality: "Redshift doesn't support indexes, so they never exist"

## Solution

**Exclude these tests** by adding `index_reflection` requirement.

### Implementation
Added to `sqlalchemy_compliance/requirements.py`:
```python
@property
def index_reflection(self):
    """Redshift doesn't support index reflection (no indexes exist)"""
    return exclusions.closed()
```

### Why This is Correct
- HasIndexTest requires `index_reflection` capability
- Redshift fundamentally doesn't support indexes (uses sort/dist keys)
- No implementation fix possible - this is a Redshift limitation
- Tests are checking a feature that doesn't exist

## Test Results

**Before**: 4 failed
**After**: 4 skipped (0 collected)

```
collected 4 items
[all skipped due to index_reflection requirement]
```

## Impact on Pass Rate

- **Tests moved**: 4 failures → 4 skipped
- **New totals**: 609 passed, 258 failed, 412 skipped
- **Pass rate**: Still ~70% (skipped tests don't count)

## Related Configuration

Existing index-related settings:
- `dialect.py`: `supports_indexes = False`
- `requirements.py`: `indexes = False`
- `requirements.py`: `index_reflection = False` (NEW)
- DDL compiler: Returns no-op for CREATE INDEX

All settings are now consistent: Redshift doesn't support indexes in any form.
