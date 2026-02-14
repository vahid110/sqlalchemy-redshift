# ReturningGuardsTest - Final Solution
**Date**: 2026-02-14
**Status**: ✅ COMPLETE - 6/6 tests passing (100%)

## Problem Summary
ReturningGuardsTest was failing because our custom DELETE compiler for USING clause was not properly handling RETURNING clauses when `delete_returning = False`.

## Solution: Hybrid Approach
Implemented different error handling based on execution context:

### For executemany (batch operations):
- Detect using `compiler.for_executemany` flag
- Raise `StatementError` at compile time with message: "Dialect redshift+psycopg2 with current server capabilities does not support DELETE...RETURNING when executemany is used"
- Prevents execution, gives clear SQLAlchemy error

### For single execution:
- Compile RETURNING clause into SQL
- Let statement go to database
- Database returns `DBAPIError` (syntax error)
- Matches test expectations

## Implementation
```python
if sa_version >= Version('1.4.0') and element._returning:
    if not compiler.dialect.delete_returning:
        for_executemany = bool(getattr(compiler, "for_executemany", False))
        
        if for_executemany:
            # Raise StatementError for batch operations
            raise exc.StatementError(msg, None, None, None)
        else:
            # Compile RETURNING for single execution, let DB error
            text += ' ' + compiler.returning_clause(...)
```

## Why This Approach is Correct

### Production Safety
1. **No silent failures**: Users always get an error when using unsupported RETURNING
2. **Clear error messages**: StatementError for executemany provides clear guidance
3. **Transaction safety**: executemany fails before hitting DB, avoiding transaction pollution

### Test Compliance
1. **test_delete_single**: Expects DBAPIError from database ✅
2. **test_delete_many**: Expects StatementError from SQLAlchemy ✅
3. Matches SQLAlchemy's standard behavior for unsupported features

### Consistency
- UPDATE/INSERT use default compiler → SQLAlchemy handles errors
- DELETE uses custom compiler → We handle errors the same way SQLAlchemy would

## Test Results
```
test_delete_many    ✅ PASSED
test_delete_single  ✅ PASSED  
test_insert_many    ✅ PASSED
test_insert_single  ✅ PASSED
test_update_many    ✅ PASSED
test_update_single  ✅ PASSED
```

**Final Score: 6/6 (100%)**

## Key Learnings
1. Custom compilers must handle dialect flags explicitly
2. Different execution contexts (single vs executemany) require different error strategies
3. Accepting test failures is NOT acceptable for production code
4. The `compiler.for_executemany` flag is key to detecting batch operations
