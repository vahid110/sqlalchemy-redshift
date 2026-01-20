# SQLAlchemy Test Suite Error Analysis

**⚠️ NOTE: This is the INITIAL error analysis. See [STATUS.md](STATUS.md) for current progress.**

**Test Run Date**: January 2025 (Initial Run)
**Total Tests**: 1,643 collected
**Results**: 352 PASSED, 133 SKIPPED, 30 FAILED, 796 ERRORS (1,311 tests executed)

## Error Breakdown by Root Cause

### 1. CHECK Constraints Not Supported (749 errors - 94.1% of all errors)
**Error**: `psycopg2.errors.FeatureNotSupported: CREATE TABLE CHECK constraint is not supported`

**Affected Test Classes**:
- ComponentReflectionTest_redshift+psycopg2_8_0_2: 749 errors

**Root Cause**: 
- Redshift does NOT support CHECK constraints in CREATE TABLE statements
- The test suite's base table fixtures include CHECK constraints
- All ComponentReflectionTest tests share the same table setup that includes:
  ```sql
  CREATE TABLE users (
    ...
    CONSTRAINT zz_test2_gt_zero CHECK (test2 > 0),
    CHECK (test2 <= 1000),
    ...
  )
  ```

**Solution Required**:
- Option A: Fix dialect DDL compiler to silently skip CHECK constraints during CREATE TABLE
- Option B: Exclude ComponentReflectionTest entirely (NOT RECOMMENDED - loses valuable reflection testing)
- Option C: Override the test fixtures to remove CHECK constraints (complex)
- **RECOMMENDED**: Option A - Fix the dialect to handle CHECK constraints gracefully

---

### 2. Quoted Table Names with Quotes/Apostrophes (18 errors - 2.3%)
**Error**: `psycopg2.errors.SyntaxError: syntax error at or near "one" in context "AND relname = 'quote ' one'"`

**Affected Test Classes**:
- QuotedNameArgumentTest_redshift+psycopg2_8_0_2: 18 errors

**Root Cause**:
- Tests use table names like `quote ' one` and `quote " two`
- Dialect's reflection queries don't properly escape quotes in table names
- SQL injection vulnerability in reflection code

**Solution Required**:
- Fix dialect's `get_columns()`, `get_foreign_keys()`, `get_indexes()`, etc. to properly escape table names
- Use parameterized queries instead of string formatting

---

### 3. Schema Does Not Exist (11 errors - 1.4%)
**Error**: `psycopg2.errors.InvalidSchemaName: schema "test_schema" does not exist`

**Affected Test Classes**:
- HasTableTest_redshift+psycopg2_8_0_2: 8 errors
- SameNamedSchemaTableTest_redshift+psycopg2_8_0_2: 3 errors

**Root Cause**:
- Tests expect schemas to be auto-created or to exist
- Redshift requires explicit schema creation
- Test setup doesn't create the required schemas

**Solution Required**:
- Add schema creation to test fixtures
- OR exclude tests that require non-existent schemas

---

### 4. ENUM Type Not Supported (7 errors - 0.9%)
**Error**: `psycopg2.errors.SyntaxError: syntax error at or near "ENUM" in context "TYPE myenum AS ENUM"`

**Affected Test Classes**:
- EnumTest_redshift+psycopg2_8_0_2: 7 errors

**Root Cause**:
- Redshift doesn't support PostgreSQL ENUM types
- Tests try to create ENUM types

**Solution Required**:
- Exclude ENUM tests via requirements.py
- Add `enum_data_type` exclusion

---

### 5. UUID Type Not Supported (7 errors - 0.9%)
**Error**: `psycopg2.errors.UndefinedObject: type "uuid" does not exist`

**Affected Test Classes**:
- UuidTest_redshift+psycopg2_8_0_2: 7 errors

**Root Cause**:
- Redshift doesn't have native UUID type
- Tests try to use UUID columns

**Solution Required**:
- Exclude UUID tests via requirements.py
- Add `uuid_data_type` exclusion

---

### 6. CREATE INDEX Not Supported (4 errors - 0.5%)
**Error**: `psycopg2.errors.FeatureNotSupported: SQL command "CREATE INDEX my_idx ON test_table (data)" not supported on Redshift tables`

**Affected Test Classes**:
- HasIndexTest_redshift+psycopg2_8_0_2: 4 errors

**Root Cause**:
- Redshift doesn't support traditional indexes
- Already excluded via `indexes` requirement, but some tests still run

**Solution Required**:
- Verify `indexes` exclusion is working
- May need additional exclusions for index-related tests

---

## Failed Tests Breakdown (30 failures)

### Category 1: DISTINCT ON (1 failure)
- `DistinctOnTest::test_distinct_on`
- **Cause**: Redshift doesn't support DISTINCT ON
- **Fix**: Add `distinct_on` exclusion to requirements.py

### Category 2: IS DISTINCT FROM (5 failures)
- `IsOrIsNotDistinctFromTest::test_is_or_is_not_distinct_from[*]`
- **Cause**: Redshift doesn't support IS DISTINCT FROM operator
- **Fix**: Add `is_distinct_from` exclusion to requirements.py

### Category 3: INSERT/UPDATE/DELETE with RETURNING (8 failures)
- `InsertBehaviorTest::test_autoclose_on_insert`
- `InsertBehaviorTest::test_empty_insert*`
- `InsertBehaviorTest::test_insert_from_select_autoinc`
- `InsertBehaviorTest::test_no_results_for_non_returning_insert[*]`
- **Cause**: Redshift has limited RETURNING support
- **Fix**: Already excluded `returning`, but may need more specific exclusions

### Category 4: IDENTITY/Autoincrement (3 failures)
- `IdentityAutoincrementTest::test_autoincrement_with_identity`
- `LastrowidTest::test_autoincrement_on_insert`
- `LastrowidTest::test_last_inserted_id`
- **Cause**: Redshift IDENTITY columns work differently than PostgreSQL
- **Fix**: May need dialect fixes or exclusions

### Category 5: Server-Side Cursors with FOR UPDATE (4 failures)
- `ServerSideCursorsTest::test_roundtrip_fetchall`
- `ServerSideCursorsTest::test_roundtrip_fetchmany`
- `ServerSideCursorsTest::test_ss_cursor_status[for_update_*]`
- **Cause**: Redshift doesn't support FOR UPDATE
- **Fix**: Add exclusion for FOR UPDATE tests

### Category 6: Schema Creation (2 failures)
- `FutureTableDDLTest::test_create_table_schema`
- `TableDDLTest::test_create_table_schema`
- **Cause**: Schema doesn't exist (same as error #3)
- **Fix**: Create schema in test setup

### Category 7: Backslash Escaping (2 failures)
- `StringTest::test_literal_backslashes`
- `TextTest::test_literal_backslashes`
- **Cause**: Redshift string escaping differences
- **Fix**: Investigate dialect's literal rendering

### Category 8: Miscellaneous (5 failures)
- `ExceptionTest::test_integrity_error`
- `LongNameBlowoutTest::test_long_convention_name[ix-_exclusions_02]` (index related)
- `ReturningGuardsTest::test_delete_many/single/update_single` (RETURNING related)

---

## Action Plan

### Priority 1: Fix CHECK Constraint Handling (Fixes 749 errors - 94%)
**File**: `sqlalchemy_redshift/dialect.py` (DDL compiler)
**Action**: Override `visit_create_table_constraint` to skip CHECK constraints
**Impact**: Will fix 749 ComponentReflectionTest errors

### Priority 2: Add Missing Exclusions (Fixes ~20 errors/failures)
**File**: `sqlalchemy_compliance/requirements.py`
**Action**: Add exclusions for:
- `distinct_on`
- `is_distinct_from`
- `uuid_data_type`
- `enum_data_type`
- `for_update` (if exists)

### Priority 3: Fix Quoted Name Handling (Fixes 18 errors)
**File**: `sqlalchemy_redshift/dialect.py` (reflection methods)
**Action**: Fix SQL injection in reflection queries
**Impact**: Security fix + 18 test errors

### Priority 4: Schema Creation (Fixes 11 errors + 2 failures)
**File**: Test fixtures or dialect
**Action**: Ensure test schemas are created before tests run

### Priority 5: Investigate Remaining Failures (13 failures)
**Action**: Analyze each failure individually to determine if it's:
- A dialect bug that needs fixing
- A feature that should be excluded
- A test that needs adjustment

---

## Expected Results After Fixes

**Conservative Estimate**:
- ERRORS: 796 → ~30 (fixing CHECK constraints + exclusions)
- FAILED: 30 → ~15 (after exclusions and schema fixes)
- PASSED: 352 → ~1,200+ (tests that were erroring will now run)
- SKIPPED: 135 → ~350 (more proper exclusions)

**Success Criteria**: 
- 70%+ pass rate (1,150+ passing tests)
- <5% error rate (<80 errors)
- All errors/failures documented and justified
