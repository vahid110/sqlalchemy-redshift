# IsOrIsNotDistinctFromTest Investigation & Fix
**Date**: 2026-02-14
**Status**: ✅ COMPLETE - 5/5 tests now skipped

## Problem
All 5 IsOrIsNotDistinctFromTest tests were failing:
- test_is_or_is_not_distinct_from[both_int_different]
- test_is_or_is_not_distinct_from[both_int_same]
- test_is_or_is_not_distinct_from[one_null_first]
- test_is_or_is_not_distinct_from[one_null_second]
- test_is_or_is_not_distinct_from[both_null]

**Error**: `ProgrammingError: syntax error at or near "DISTINCT"`

## Root Cause
Redshift doesn't support the `IS [NOT] DISTINCT FROM` operator.

**SQL Generated**:
```sql
WHERE is_distinct_test.col_a IS NOT DISTINCT FROM is_distinct_test.col_b
```

**Redshift Response**: Syntax error - operator not recognized

## Solution
Add `supports_is_distinct_from` requirement exclusion.

**Issue**: We had `is_distinct_from = False` but test checks `supports_is_distinct_from`

### Implementation
Added to `sqlalchemy_compliance/requirements.py`:
```python
@property
def supports_is_distinct_from(self):
    """Redshift doesn't support IS DISTINCT FROM operator"""
    return exclusions.closed()
```

## Why This Operator Doesn't Exist in Redshift

`IS [NOT] DISTINCT FROM` is a SQL standard operator that:
- Treats NULL as a comparable value
- `a IS NOT DISTINCT FROM b` returns TRUE if both are NULL
- Regular `=` returns NULL when comparing NULLs

**Workaround** (if needed in production):
```sql
-- Instead of: a IS NOT DISTINCT FROM b
-- Use: (a = b) OR (a IS NULL AND b IS NULL)
```

But for tests, proper exclusion is correct.

## Test Results

**Before**: 5 failed
**After**: 5 skipped

```
collected 5 items
[all 5 skipped due to supports_is_distinct_from requirement]
```

## Impact on Pass Rate

- **Tests moved**: 5 failures → 5 skipped
- **New totals**: 609 passed, ~249 failed, ~421 skipped
- **Pass Rate**: Still ~70% (skipped tests don't count)

## Related Configuration

- `requirements.py`: `is_distinct_from = False` (kept for compatibility)
- `requirements.py`: `supports_is_distinct_from = False` (NEW - what test checks)

Both exclusions document that Redshift doesn't support this operator.
