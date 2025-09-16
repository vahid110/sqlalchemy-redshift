# SQLAlchemy 2.0 Modernization Implementation Checklist

## Phase 1: Foundation (Weeks 1-2)

### Week 1: Core Architecture
- [x] **Capability Flags Enhancement**
  - [x] Add `insert_returning = False`
  - [x] Add `use_insertmanyvalues = False`
  - [x] Add `supports_sane_rowcount = False`
  - [x] Add `supports_statement_cache = True`
  - [ ] Verify existing boolean/decimal/uuid flags
  - [ ] Test capability flags with SQLAlchemy 1.4 & 2.0

- [x] **Authentication System Migration**
  - [x] Create `sqlalchemy_redshift/auth.py`
  - [x] Migrate `create_profile_engine()` helper
  - [x] Migrate `create_serverless_engine()` helper
  - [x] Migrate `create_saml_engine()` helper
  - [x] Migrate `create_azure_engine()` helper
  - [x] Implement comprehensive URL parameter parsing
  - [x] Add credential redaction in logs
  - [ ] Test all 9 authentication methods

- [x] **Error Handling & Resilience**
  - [x] Create `sqlalchemy_redshift/resilience.py`
  - [x] Migrate `ProductionErrorHandler` class
  - [x] Migrate `CircuitBreaker` implementation
  - [x] Add retry logic with exponential backoff
  - [x] Enhance `is_disconnect()` method
  - [x] Improve `do_rollback()` with cache clearing
  - [x] Add connection health monitoring

### Week 2: Type System & Reflection
- [x] **Enhanced Type Support**
  - [x] Add `ABSTIME` type to ischema_names
  - [x] Add `INTERVAL` type to ischema_names
  - [x] Enhance `SUPER` type with caching
  - [x] Add `JSON` type with error handling
  - [x] Improve `RedshiftArray` performance
  - [ ] Test type round-trips

- [x] **Inspector-First Reflection**
  - [x] Modernize reflection to use Inspector pattern
  - [x] Optimize bulk reflection queries (`get_multi_columns`)
  - [x] Add Redshift-specific metadata support
  - [x] Implement reflection caching
  - [ ] Test reflection accuracy vs original

## Phase 2: Feature Migration (Weeks 3-4)

### Week 3: Command Integration
- [x] **COPY/UNLOAD Commands**
  - [x] Preserve existing `CopyCommand` functionality
  - [x] Preserve existing `UnloadFromSelect` functionality
  - [x] Enhance with improved credential handling
  - [x] Add streaming support for large operations
  - [x] Document autocommit requirements
  - [x] Test command compilation and execution

- [x] **DDL Extensions**
  - [x] Maintain `DISTSTYLE` support in DDL compiler
  - [x] Maintain `DISTKEY` support in DDL compiler
  - [x] Maintain `SORTKEY` support in DDL compiler
  - [x] Add `IDENTITY` column handling
  - [x] Enhance materialized view support
  - [x] Implement table option reflection
  - [x] Test DDL compilation accuracy

### Week 4: Performance & Streaming
- [x] **Connection Management**
  - [x] Implement optimized `get_pool_class()`
  - [x] Enhance `on_connect()` with Redshift parameters
  - [x] Add connection parameter optimization
  - [x] Test connection pooling performance

- [x] **Streaming & Fetch Size**
  - [x] Add execution options for streaming
  - [x] Implement configurable fetch sizes
  - [x] Add memory-efficient result processing
  - [x] Test streaming with large result sets

## Phase 3: Production Ready (Weeks 5-6)

### Week 5: Testing Matrix
- [ ] **Comprehensive Test Suite**
  - [ ] Set up CI matrix (Python 3.9-3.12)
  - [x] Set up SQLAlchemy version matrix (1.4.x, 2.0.x)
  - [x] Set up driver matrix (redshift_connector, psycopg2, psycopg2cffi)
  - [ ] Configure test environment

- [ ] **Golden Tests**
  - [ ] SQL compilation tests for all DDL features
  - [ ] Type round-trip tests (SUPER, GEOMETRY, etc.)
  - [ ] Reflection accuracy tests with mocked data
  - [ ] Authentication tests for all 9 methods
  - [ ] Performance regression tests

### Week 6: Documentation & Polish
- [ ] **Documentation Overhaul**
  - [ ] Create feature matrix (PostgreSQL vs Redshift vs Dialect)
  - [ ] Write authentication guide with security best practices
  - [ ] Create performance tuning guide
  - [ ] Write migration guide from 1.4 to 2.0
  - [ ] Update README with new features

- [ ] **Developer Experience**
  - [ ] Add type hints throughout codebase
  - [ ] Implement clear error messages for unsupported features
  - [ ] Create examples for common patterns
  - [ ] Write troubleshooting guide
  - [ ] Add docstrings to all public methods

## Quality Assurance Checklist

### Code Quality
- [ ] **Linting & Formatting**
  - [ ] Set up `ruff` for linting
  - [ ] Set up `black` for formatting
  - [ ] Set up `isort` for import sorting
  - [ ] Set up `mypy` for type checking
  - [ ] Configure `pre-commit` hooks

- [ ] **Testing Standards**
  - [ ] Achieve 100% test coverage for new code
  - [ ] All tests pass on Python 3.9-3.12
  - [ ] All tests pass on SQLAlchemy 1.4 & 2.0
  - [ ] Performance tests show no regression
  - [ ] Memory usage tests for streaming

### Security & Reliability
- [ ] **Security Measures**
  - [ ] Credential redaction in all log outputs
  - [ ] Secure handling of authentication tokens
  - [ ] Input validation for all URL parameters
  - [ ] SQL injection prevention verification

- [ ] **Reliability Features**
  - [ ] Connection health checks working
  - [ ] Retry logic tested with transient failures
  - [ ] Circuit breaker tested with connection issues
  - [ ] Graceful degradation for auth failures

## Compatibility Verification

### SQLAlchemy 1.4 Compatibility
- [x] All features work with SQLAlchemy 1.4.x
- [x] No deprecation warnings in 1.4
- [x] Reflection works correctly in 1.4
- [x] Authentication works in 1.4
- [x] COPY/UNLOAD commands work in 1.4

### SQLAlchemy 2.0 Compatibility
- [ ] All features work with SQLAlchemy 2.0.x
- [ ] Modern patterns used throughout
- [ ] Inspector-based reflection working
- [ ] Statement caching enabled and working
- [ ] No legacy API usage

### Driver Compatibility
- [x] **redshift_connector**
  - [x] All authentication methods working
  - [x] Performance optimizations active
  - [x] Streaming functionality working
  
- [x] **psycopg2**
  - [x] Basic functionality maintained
  - [x] SSL configuration working
  - [x] Legacy compatibility preserved
  
- [x] **psycopg2cffi**
  - [x] Basic functionality maintained
  - [x] PyPy compatibility verified

## Final Validation

### Performance Benchmarks
- [ ] Connection establishment time ≤ baseline
- [ ] Query execution time ≤ baseline
- [ ] Memory usage ≤ baseline for large results
- [ ] Reflection time ≤ baseline

### User Experience
- [ ] Clear error messages for common issues
- [ ] Comprehensive documentation available
- [ ] Migration path documented
- [ ] Examples work as documented

### Community Readiness
- [ ] Code review completed
- [ ] Documentation review completed
- [ ] Community feedback incorporated
- [ ] Release notes prepared

## CRITICAL BLOCKERS FOR TRUE SA 2.0 COMPATIBILITY

### Phase 4: True SA 2.0 Compatibility (Critical Issues)

- [x] **1. Packaging Constraint (CRITICAL)**
  - [x] Update setup.py: `SQLAlchemy>=1.4.48,<3` (currently `<2.0.0`)
  - [x] Add Python 3.10-3.12 classifiers
  - [x] Update python_requires to >=3.8 (dropped 3.4-3.7)
  - [x] Test installation with SA 2.0.x
  - [ ] Document URL forms for psycopg2/redshift-connector extras

- [ ] **2. Test Modernization (CRITICAL)**
  - [ ] Replace `select([col])` → `select(col)` throughout tests
  - [ ] Remove `engine.execute` → use `conn.execute`
  - [ ] Update to new `Result`/`Row` API patterns
  - [ ] Add bulk insert tests (identity cols, NULLs, JSON/SUPER, arrays)
  - [ ] Enable warnings-as-errors to catch deprecations

- [ ] **3. Compiler Internals (CRITICAL)**
  - [ ] Stop reading private `Select` attrs (`_limit_clause`, `_limit`)
  - [ ] Override visitors via public hooks (follow PostgreSQL patterns)
  - [ ] Add tests for LIMIT/OFFSET with CTEs, subqueries, ORDER BY
  - [ ] Validate DELETE...USING compilation

- [ ] **4. Reflection & Inspector (HIGH)**
  - [ ] Use `inspect(engine)` calls instead of direct dialect methods
  - [ ] Fix `has_table`, `get_table_names`, `get_foreign_keys` signatures
  - [ ] Suppress SA 2.0 deprecation warnings
  - [ ] Test Inspector-based reflection patterns

- [ ] **5. Bulk Insert Validation (HIGH)**
  - [ ] Test `use_insertmanyvalues=True` with complex types
  - [ ] Validate with `insert_returning=False` constraint
  - [ ] Test ORM bulk operations with SUPER/JSON/arrays
  - [ ] Verify no hidden RETURNING assumptions

- [ ] **6. Resilience Integration (MEDIUM)**
  - [ ] Wire circuit breakers into `do_execute`/`do_executemany`
  - [ ] Implement `is_disconnect` for pool recycling
  - [ ] Add configurable transient-error retry
  - [ ] Enable pool pre-ping documentation

- [ ] **7. Driver Matrix Testing (MEDIUM)**
  - [ ] Update tox.ini: Add SA 2.0.x environments (currently only SA 1.3/1.4)
  - [ ] Tox matrix: Py 3.8-3.12 × SA 1.4/2.0 × drivers
  - [ ] Add redshift_connector to tox environments (not just pytest args)
  - [ ] Test statement caching across drivers
  - [ ] Validate paramstyles and compilation
  - [ ] Test repeated compilation scenarios

- [ ] **8. Alembic Integration (LOW)**
  - [ ] Create smoke migration test
  - [ ] Test with Alembic 1.12/1.13 + SA 2.0
  - [ ] Validate DDL compilation in migrations
  - [ ] Test create table → add column → drop column

## Success Criteria (All Must Pass)
- [ ] ✅ All 8 critical blockers resolved
- [ ] ✅ Packaging allows SA 2.0 installation
- [ ] ✅ All tests pass with SA 1.4 AND 2.0
- [ ] ✅ No private API usage in compiler
- [ ] ✅ Modern Inspector patterns used
- [ ] ✅ Bulk operations validated with complex types
- [ ] ✅ Resilience features wired into execution
- [ ] ✅ Multi-driver matrix testing complete
- [ ] ✅ Alembic migration compatibility verified

---

**Total Items:** 100+ checklist items across 6 weeks
**Completion Tracking:** Use this checklist to track progress and ensure nothing is missed
**Review Points:** Weekly review of completed items and blockers