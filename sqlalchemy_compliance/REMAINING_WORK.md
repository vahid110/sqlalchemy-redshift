# Remaining Work - SQLAlchemy Compliance Test Suite

## Current Status
- **444 PASSED** (+37 from before)
- **427 FAILED** (-37 from before)
- **408 SKIPPED** (unchanged)
- **32 ERRORS** (unchanged)

## Priority 6: ObjectScope Filtering (TEMPORARY tables)

### Issue
Multi-reflection tests with `ObjectScope.TEMPORARY` are failing because we don't filter temporary tables.

### Pattern
All failures include `ObjectScope.TEMPORARY` or `ObjectScope.ANY` (which includes temporary).

### Solution
Add scope filtering to `get_multi_*` methods:
- `ObjectScope.DEFAULT` - exclude temporary tables
- `ObjectScope.TEMPORARY` - only temporary tables  
- `ObjectScope.ANY` - include all tables

### Implementation
Modify `get_table_names()` and `get_view_names()` to accept `scope` parameter and filter accordingly.

## Priority 7: Materialized View Support

### Issue
Tests with `ObjectKind.MATERIALIZED_VIEW` fail because we don't query materialized views.

### Solution
Add `get_materialized_view_names()` method and include in multi-reflection filtering.

## Priority 8: Test Environment Issues

### Issue
Some tests show non-existent tables like `('test_schema', 'does-not-exist')` in results.

### Root Cause
Tests intentionally pass non-existent table names to verify error handling.

### Solution
Already handled - our try/except in `get_multi_*` methods skips non-existent tables.

## Priority 9: Quoted Name Tests

### Issue
Tests with quoted names (spaces, dots, mixed case) are failing.

### Examples
- `FK_users_id`
- `mixedCaseName`
- `ix.with.dots`

### Solution
Verify our identifier handling preserves quotes correctly.

## Priority 10: Index Tests

### Issue
Index tests fail even though we return empty list (correct for Redshift).

### Root Cause
Tests may expect specific error messages or behavior.

### Solution
Review test expectations and adjust if needed.

## Recommended Order

1. **Priority 6** (ObjectScope) - Will fix ~100+ tests
2. **Priority 7** (Materialized Views) - Will fix ~50+ tests
3. **Priority 9** (Quoted Names) - Will fix ~20+ tests
4. **Priority 8** (Test Environment) - Already handled
5. **Priority 10** (Indexes) - Low priority, may be test expectations

## Estimated Impact

Fixing Priorities 6-7 should bring us to:
- **~600 PASSED** (from 444)
- **~270 FAILED** (from 427)
- **408 SKIPPED** (unchanged)

This would be **~73% pass rate** on non-skipped tests.
