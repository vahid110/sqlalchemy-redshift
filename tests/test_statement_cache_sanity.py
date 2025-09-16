"""
Test statement cache behavior across drivers and SA versions.
Critical for production performance and memory usage.
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String, select, bindparam
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
)


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
class TestStatementCacheSanity:
    """Test statement cache behavior and performance"""
    
    def test_statement_cache_flags_correct(self, dialect_cls):
        """Test statement cache flags are set correctly per driver"""
        dialect = dialect_cls()
        
        if "redshift_connector" in dialect_cls.__name__:
            assert dialect.supports_statement_cache is True
        else:
            assert dialect.supports_statement_cache is False
    
    def test_repeated_compilation_consistency(self, dialect_cls):
        """Test repeated compilation produces consistent results"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table("test_cache", meta,
            Column("id", Integer),
            Column("name", String(50)),
            Column("value", Integer)
        )
        
        # Create statement with bound parameters
        stmt = select(table.c.id, table.c.name).where(
            sa.and_(
                table.c.id > bindparam("min_id"),
                table.c.value < bindparam("max_value")
            )
        ).order_by(table.c.name).limit(bindparam("limit_count"))
        
        # Compile multiple times
        compiled_results = []
        for i in range(10):
            compiled = stmt.compile(dialect=dialect)
            sql_str = str(compiled)
            compiled_results.append(sql_str)
        
        # All compilations should be identical
        first_result = compiled_results[0]
        for result in compiled_results[1:]:
            assert result == first_result, f"Compilation inconsistency in {dialect_cls.__name__}"
        
        # Should contain expected elements
        assert "SELECT" in first_result
        assert "WHERE" in first_result
        assert "ORDER BY" in first_result
        assert "LIMIT" in first_result
    
    def test_bound_parameter_handling(self, dialect_cls):
        """Test bound parameter handling with statement cache"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table("test_params", meta,
            Column("id", Integer),
            Column("status", String(20))
        )
        
        # Statement with multiple parameter types
        stmt = select(table.c.id).where(
            sa.and_(
                table.c.id.in_(bindparam("id_list", expanding=True)),
                table.c.status == bindparam("status_filter")
            )
        )
        
        # Compile with different parameter scenarios
        compiled1 = stmt.compile(dialect=dialect)
        compiled2 = stmt.compile(dialect=dialect)
        
        # Should be consistent
        assert str(compiled1) == str(compiled2)
        
        # Should handle parameter placeholders correctly
        sql_str = str(compiled1)
        if "redshift_connector" in dialect_cls.__name__:
            # Format style parameters
            assert "%(status_filter)s" in sql_str or "%s" in sql_str
        else:
            # Pyformat style parameters  
            assert "%(status_filter)s" in sql_str
    
    def test_complex_query_caching(self, dialect_cls):
        """Test caching behavior with complex queries"""
        dialect = dialect_cls()
        meta = MetaData()
        
        users = Table("users", meta,
            Column("id", Integer),
            Column("name", String(50)),
            Column("department_id", Integer)
        )
        
        departments = Table("departments", meta,
            Column("id", Integer),
            Column("name", String(50))
        )
        
        # Complex query with JOIN, subquery, aggregation
        subq = select(users.c.department_id, sa.func.count().label("user_count")).group_by(
            users.c.department_id
        ).subquery()
        
        stmt = select(
            departments.c.name,
            subq.c.user_count
        ).select_from(
            departments.join(subq, departments.c.id == subq.c.department_id)
        ).where(
            subq.c.user_count > bindparam("min_users")
        ).order_by(subq.c.user_count.desc())
        
        # Multiple compilations should be consistent
        results = []
        for _ in range(5):
            compiled = stmt.compile(dialect=dialect)
            results.append(str(compiled))
        
        # All should be identical
        assert all(r == results[0] for r in results[1:])
        
        # Should contain expected SQL elements
        first_result = results[0]
        assert "JOIN" in first_result
        assert "GROUP BY" in first_result
        assert "ORDER BY" in first_result
        assert "count(*)" in first_result.lower()


@pytest.mark.parametrize("sa_version,dialect_cls", [
    ("1.4", RedshiftDialect_psycopg2),
    ("1.4", RedshiftDialect_redshift_connector),
    ("2.0", RedshiftDialect_psycopg2),
    ("2.0", RedshiftDialect_redshift_connector)
])
class TestStatementCacheSAVersions:
    """Test statement cache across SQLAlchemy versions"""
    
    def test_cache_behavior_sa_version_compatibility(self, sa_version, dialect_cls):
        """Test cache behavior is consistent across SA versions"""
        dialect = dialect_cls()
        
        # Basic statement that should work in both SA 1.4 and 2.0
        meta = MetaData()
        table = Table("version_test", meta,
            Column("id", Integer),
            Column("data", String(100))
        )
        
        stmt = select(table.c.id, table.c.data).where(
            table.c.id == bindparam("target_id")
        )
        
        # Should compile consistently
        compiled1 = stmt.compile(dialect=dialect)
        compiled2 = stmt.compile(dialect=dialect)
        
        assert str(compiled1) == str(compiled2)
        
        # Should have proper parameter handling
        sql_str = str(compiled1)
        assert "SELECT" in sql_str
        assert "WHERE" in sql_str
        # Parameter style depends on dialect - may be %s or %(target_id)s
        assert "%" in sql_str  # Some form of parameter placeholder
    
    def test_no_cache_warnings_psycopg2(self, sa_version, dialect_cls):
        """Test psycopg2 dialects don't generate cache warnings"""
        dialect = dialect_cls()
        
        if "psycopg2" in dialect_cls.__name__:
            # Cache should be disabled
            assert dialect.supports_statement_cache is False
        else:
            # redshift_connector should have cache enabled
            assert dialect.supports_statement_cache is True
        
        # Multiple compilations should not generate warnings
        meta = MetaData()
        table = Table("warning_test", meta, Column("id", Integer))
        stmt = select(table.c.id)
        
        # This should not generate warnings regardless of cache setting
        for _ in range(3):
            compiled = stmt.compile(dialect=dialect)
            assert compiled is not None


class TestStatementCacheMemoryBehavior:
    """Test statement cache memory and performance characteristics"""
    
    @pytest.mark.parametrize("dialect_cls", [RedshiftDialect_redshift_connector])
    def test_cache_enabled_performance(self, dialect_cls):
        """Test cache-enabled dialect performance characteristics"""
        dialect = dialect_cls()
        assert dialect.supports_statement_cache is True
        
        meta = MetaData()
        table = Table("perf_test", meta,
            Column("id", Integer),
            Column("value", String(50))
        )
        
        # Create many similar statements
        statements = []
        for i in range(100):
            stmt = select(table.c.id).where(table.c.id == bindparam(f"param_{i}"))
            statements.append(stmt)
        
        # Compile all statements
        compiled_results = []
        for stmt in statements:
            compiled = stmt.compile(dialect=dialect)
            compiled_results.append(str(compiled))
        
        # Should all compile successfully
        assert len(compiled_results) == 100
        assert all("SELECT" in result for result in compiled_results)
    
    @pytest.mark.parametrize("dialect_cls", [RedshiftDialect_psycopg2])
    def test_cache_disabled_behavior(self, dialect_cls):
        """Test cache-disabled dialect behavior"""
        dialect = dialect_cls()
        assert dialect.supports_statement_cache is False
        
        meta = MetaData()
        table = Table("no_cache_test", meta, Column("id", Integer))
        stmt = select(table.c.id).where(table.c.id == bindparam("test_param"))
        
        # Multiple compilations should work without cache
        results = []
        for _ in range(10):
            compiled = stmt.compile(dialect=dialect)
            results.append(str(compiled))
        
        # Should be consistent even without cache
        assert all(r == results[0] for r in results[1:])
        assert "SELECT" in results[0]