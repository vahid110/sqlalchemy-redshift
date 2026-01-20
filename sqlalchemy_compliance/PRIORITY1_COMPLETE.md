# Priority 1 Fix: Server-Side Cursor Issue - COMPLETED ✅

**Date**: January 2025  
**Issue**: Redshift's "opening multiple cursors from within the same client connection is not allowed" error  
**Impact**: 749+ ComponentReflectionTest errors

## Problem

Redshift allows only one cursor per connection. When tests use server-side cursors and call `has_table()` during table creation (`checkfirst=True`), the dialect's reflection code opens a second cursor, causing the error:

```
psycopg2.errors.InvalidCursorState: opening multiple cursors from within the same client connection is not allowed.
```

## Solution

Modified `has_table()` and `_get_all_relation_info()` in `sqlalchemy_redshift/dialect.py`:

1. **has_table()**: Passes `_has_table_check=True` flag to signal client-side cursor needed
2. **_get_all_relation_info()**: When flag is set, uses `execution_options(stream_results=False)` on the query to disable server-side cursor

### Code Changes

```python
# In has_table()
kw['_has_table_check'] = True
table = self._get_all_relation_info(connection, schema=schema, 
                                     table_name=table_name, 
                                     info_cache=info_cache, **kw)

# In _get_all_relation_info()
if kw.get('_has_table_check'):
    result = connection.execute(query.execution_options(stream_results=False))
else:
    result = connection.execute(query)
```

## Why This Approach

✅ **Targeted**: Only affects `has_table()` calls, not all reflection  
✅ **Memory-safe**: Doesn't use `fetchall()` on potentially large result sets  
✅ **Minimal**: Small, focused change  
✅ **Production-safe**: Other reflection methods continue using server-side cursors when appropriate

## Verification

**Before**: ComponentReflectionTest failed immediately with cursor error  
**After**: ComponentReflectionTest proceeds past cursor issue, now fails on different issues (CREATE INDEX, etc.)

Example test that now works past cursor issue:
```bash
pytest test_suite.py::ServerSideCursorsTest::test_roundtrip_fetchmany
# Before: InvalidCursorState error
# After: Proceeds to INSERT test (fails on different issue - IDENTITY column)
```

## Next Steps

The cursor fix is complete. Remaining errors are different issues:
- CREATE INDEX not supported (needs exclusion)
- IDENTITY column behavior differences
- Schema creation issues
- Quoted name SQL injection

See STATUS.md for Priority 2-5 fixes.
