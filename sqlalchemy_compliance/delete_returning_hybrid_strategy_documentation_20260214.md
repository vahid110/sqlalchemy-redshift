# DELETE RETURNING Hybrid Strategy - Documentation
**Date**: 2026-02-14
**Status**: ✅ Implemented and Documented

## Executive Summary

The Redshift dialect uses a **hybrid error strategy** for DELETE...RETURNING to balance production safety, test compliance, and Redshift's actual behavior.

**Key Point**: Redshift does NOT support RETURNING in DELETE statements. Users will ALWAYS get an error if they try to use it. The hybrid strategy ensures appropriate error types for different contexts.

## The Challenge

Redshift doesn't support DELETE...RETURNING, but we have a custom DELETE compiler (for USING clause support). This creates a dilemma:

1. **Strip RETURNING silently**: DANGEROUS - user gets no error, no data returned
2. **Always fail at compile time**: Clean, but breaks SQLAlchemy test expectations
3. **Always let DB fail**: Works, but wrong error type for batch operations
4. **Hybrid approach**: Different strategies for different contexts ✅

## The Solution: Hybrid Error Strategy

### For Batch Operations (executemany)
```python
if for_executemany:
    raise exc.StatementError(
        "Dialect redshift+psycopg2 does not support "
        "DELETE...RETURNING when executemany is used"
    )
```

**Why**: 
- Prevents transaction pollution (DB errors can abort transactions)
- Provides clear SQLAlchemy error message
- Fails before any database interaction
- Matches SQLAlchemy's standard behavior for unsupported features

**User Experience**:
```python
# User code
connection.execute(
    delete(table).returning(table.c.id),
    [{"id": 1}, {"id": 2}, {"id": 3}]
)

# Result: StatementError with clear message
# "Dialect redshift+psycopg2 does not support DELETE...RETURNING when executemany is used"
```

### For Single Execution
```python
else:
    # Compile RETURNING into SQL
    text += ' ' + compiler.returning_clause(...)
```

**Why**:
- Matches PostgreSQL-family error behavior
- SQLAlchemy tests expect DBAPIError from database
- Error is immediate and clear (not silent)
- Redshift returns: "syntax error at or near RETURNING"

**User Experience**:
```python
# User code
connection.execute(
    delete(table).where(table.c.id == 1).returning(table.c.id)
)

# Result: ProgrammingError (DBAPIError) from Redshift
# "syntax error at or near RETURNING"
```

## Why Compile Unsupported RETURNING?

**This is a deliberate compromise for test compliance.**

### The Concern
"Aren't we misleading users by compiling RETURNING when it's not supported?"

### The Answer
**No, because:**

1. **Users ALWAYS get an error** - never silent success
2. **The error is immediate and clear** - happens on first execution
3. **No data loss risk** - operation fails before modifying data
4. **Matches database family behavior** - PostgreSQL-based systems error at DB level
5. **Test compliance** - SQLAlchemy's ReturningGuardsTest expects this behavior

### Alternative Considered: Always Fail at Compile Time

```python
# Rejected approach
if element._returning:
    raise exc.CompileError("Redshift doesn't support DELETE...RETURNING")
```

**Why rejected**:
- Breaks SQLAlchemy test expectations
- Tests expect DBAPIError for single execution
- Would require test exclusions (pipeline implications)
- Current approach is equally safe for users

## Production Safety Guarantees

### ✅ No Silent Failures
- Executemany: StatementError before execution
- Single: DBAPIError from database
- Both are clear, immediate errors

### ✅ No Data Loss
- Operations fail before modifying data
- Transactions remain clean (especially for executemany)
- Users cannot accidentally lose RETURNING data

### ✅ Clear Error Messages
- Executemany: "does not support DELETE...RETURNING when executemany is used"
- Single: "syntax error at or near RETURNING"
- Both clearly indicate the feature is unsupported

### ✅ Consistent with Dialect Flags
- `delete_returning = False` indicates no support
- Hybrid strategy respects this flag
- Different error paths, same outcome: operation fails

## Test Compliance

**ReturningGuardsTest: 6/6 PASSING (100%)**

- test_delete_many ✅ - Expects StatementError, gets StatementError
- test_delete_single ✅ - Expects DBAPIError, gets DBAPIError  
- test_insert_many ✅ - Default compiler handles correctly
- test_insert_single ✅ - Default compiler handles correctly
- test_update_many ✅ - Default compiler handles correctly
- test_update_single ✅ - Default compiler handles correctly

## Documentation

### In Code
- **Docstring**: 50+ lines explaining strategy, rationale, alternatives
- **Inline comments**: Explain each code path and why it exists
- **Examples**: Show expected behavior for both contexts

### In Files
- `returning_guards_final_solution_20260214.md`: Implementation details
- `delete_returning_strategy_revision_20260214.md`: Decision analysis
- `delete_returning_final_decision_20260214.md`: Options comparison
- This file: Comprehensive explanation for stakeholders

## Conclusion

The hybrid strategy is a **pragmatic solution** that:
- ✅ Keeps users safe (always errors, never silent)
- ✅ Passes all tests (no pipeline implications)
- ✅ Matches database behavior (PostgreSQL-family expectations)
- ✅ Is well-documented (future maintainers understand why)

**This is not a hack - it's a thoughtful compromise that serves all stakeholders.**
