import pytest
from sqlalchemy import (
    func, select, text, Integer, String, Boolean, DateTime,
    Column, Table, MetaData, and_, or_, not_, case, cast,
    literal_column, bindparam
)
from sqlalchemy.sql import operators
from sqlalchemy.dialects import postgresql
from sqlalchemy_redshift.dialect import (
    RedshiftDialect_psycopg2,
    RedshiftDialect_psycopg2cffi, 
    RedshiftDialect_redshift_connector
)


def test_func_now(stub_redshift_dialect):
    """Test NOW() function compilation to SYSDATE"""
    dialect = stub_redshift_dialect
    s = select(func.NOW().label("time"))
    compiled = s.compile(dialect=dialect)
    assert str(compiled) == "SELECT SYSDATE AS time"


def test_redshift_functions(stub_redshift_dialect):
    """Test Redshift-specific function compilation
    
    Note: SQLAlchemy normalizes function names to lowercase in compiled SQL,
    so we use case-insensitive assertions. This behavior is consistent
    between SQLAlchemy 1.4 and 2.0.
    """
    dialect = stub_redshift_dialect
    
    # Test SYSDATE (Redshift equivalent of NOW) - case insensitive
    s = select(func.SYSDATE())
    compiled = s.compile(dialect=dialect)
    assert "sysdate" in str(compiled).lower()
    
    # Test GETDATE (another Redshift time function)
    s = select(func.GETDATE())
    compiled = s.compile(dialect=dialect)
    assert "getdate" in str(compiled).lower()
    
    # Test DATEADD function
    s = select(func.DATEADD(literal_column("'day'"), 1, func.SYSDATE()))
    compiled = s.compile(dialect=dialect)
    assert "dateadd" in str(compiled).lower()
    
    # Test DATEDIFF function
    s = select(func.DATEDIFF(literal_column("'day'"), func.SYSDATE(), func.SYSDATE()))
    compiled = s.compile(dialect=dialect)
    assert "datediff" in str(compiled).lower()


def test_json_functions(stub_redshift_dialect):
    """Test JSON/SUPER function compilation"""
    dialect = stub_redshift_dialect
    
    # Test JSON_PARSE function
    s = select(func.JSON_PARSE("'{\"key\": \"value\"}'")); 
    compiled = s.compile(dialect=dialect)
    assert "JSON_PARSE" in str(compiled)
    
    # Test JSON_EXTRACT_PATH_TEXT function
    s = select(func.JSON_EXTRACT_PATH_TEXT(literal_column("super_col"), "key"))
    compiled = s.compile(dialect=dialect)
    assert "JSON_EXTRACT_PATH_TEXT" in str(compiled)
    
    # Test IS_VALID_JSON function
    s = select(func.IS_VALID_JSON("'{\"key\": \"value\"}'")); 
    compiled = s.compile(dialect=dialect)
    assert "IS_VALID_JSON" in str(compiled)


def test_string_functions(stub_redshift_dialect):
    """Test string function compilation"""
    dialect = stub_redshift_dialect
    
    # Test REGEXP_REPLACE function
    s = select(func.REGEXP_REPLACE("text", "pattern", "replacement"))
    compiled = s.compile(dialect=dialect)
    assert "REGEXP_REPLACE" in str(compiled)
    
    # Test SPLIT_PART function
    s = select(func.SPLIT_PART("text", "delimiter", 1))
    compiled = s.compile(dialect=dialect)
    assert "SPLIT_PART" in str(compiled)
    
    # Test LISTAGG function
    s = select(func.LISTAGG(literal_column("col"), ","))
    compiled = s.compile(dialect=dialect)
    assert "LISTAGG" in str(compiled)


def test_window_functions(stub_redshift_dialect):
    """Test window function compilation"""
    dialect = stub_redshift_dialect
    
    # Test ROW_NUMBER
    s = select(func.ROW_NUMBER().over())
    compiled = s.compile(dialect=dialect)
    assert "row_number() over" in str(compiled).lower()
    
    # Test RANK
    s = select(func.RANK().over(order_by=literal_column("col")))
    compiled = s.compile(dialect=dialect)
    assert "rank() over" in str(compiled).lower()
    
    # Test LAG/LEAD
    s = select(func.LAG(literal_column("col"), 1).over(order_by=literal_column("col")))
    compiled = s.compile(dialect=dialect)
    assert "lag" in str(compiled).lower() and "over" in str(compiled).lower()


def test_aggregate_functions(stub_redshift_dialect):
    """Test aggregate function compilation"""
    dialect = stub_redshift_dialect
    
    # Test APPROXIMATE COUNT DISTINCT
    s = select(func.APPROXIMATE(func.COUNT(func.DISTINCT(literal_column("col")))))
    compiled = s.compile(dialect=dialect)
    assert "approximate" in str(compiled).lower()
    
    # Test MEDIAN
    s = select(func.MEDIAN(literal_column("col")))
    compiled = s.compile(dialect=dialect)
    assert "median" in str(compiled).lower()
    
    # Test PERCENTILE_CONT
    s = select(func.PERCENTILE_CONT(0.5).within_group(literal_column("col")))
    compiled = s.compile(dialect=dialect)
    assert "percentile_cont" in str(compiled).lower()


def test_operators(stub_redshift_dialect):
    """Test operator compilation"""
    dialect = stub_redshift_dialect
    
    # Test modulo operator (should use %%)
    col1 = literal_column("col1")
    col2 = literal_column("col2")
    s = select(col1 % col2)
    compiled = s.compile(dialect=dialect)
    # Note: The actual % -> %% conversion happens in post_process_text
    assert "%" in str(compiled)
    
    # Test ILIKE operator
    s = select(literal_column("col").ilike("pattern"))
    compiled = s.compile(dialect=dialect)
    assert "ILIKE" in str(compiled).upper()
    
    # Test SIMILAR TO operator
    s = select(text("col SIMILAR TO 'pattern'"))
    compiled = s.compile(dialect=dialect)
    assert "SIMILAR TO" in str(compiled)


def test_case_expressions(stub_redshift_dialect):
    """Test CASE expression compilation"""
    dialect = stub_redshift_dialect
    
    # Test simple CASE
    s = select(case(
        (literal_column("col") == 1, "one"),
        (literal_column("col") == 2, "two"),
        else_="other"
    ))
    compiled = s.compile(dialect=dialect)
    compiled_str = str(compiled).upper()
    assert "CASE" in compiled_str and "WHEN" in compiled_str and "ELSE" in compiled_str
    
    # Test simple value-based CASE (avoid dictionary syntax which has issues)
    s = select(case(
        (literal_column("status") == "active", "Active User"),
        (literal_column("status") == "inactive", "Inactive User"),
        else_="Unknown"
    ))
    compiled = s.compile(dialect=dialect)
    assert "case" in str(compiled).lower()


def test_cast_expressions(stub_redshift_dialect):
    """Test CAST expression compilation"""
    dialect = stub_redshift_dialect
    
    # Test CAST to INTEGER
    s = select(cast(literal_column("col"), Integer))
    compiled = s.compile(dialect=dialect)
    assert "CAST" in str(compiled) and "INTEGER" in str(compiled)
    
    # Test CAST to VARCHAR
    s = select(cast(literal_column("col"), String(50)))
    compiled = s.compile(dialect=dialect)
    assert "CAST" in str(compiled) and "VARCHAR" in str(compiled)
    
    # Test CAST to BOOLEAN
    s = select(cast(literal_column("col"), Boolean))
    compiled = s.compile(dialect=dialect)
    assert "CAST" in str(compiled) and "BOOLEAN" in str(compiled)


def test_boolean_expressions(stub_redshift_dialect):
    """Test boolean expression compilation"""
    dialect = stub_redshift_dialect
    
    col1 = literal_column("col1")
    col2 = literal_column("col2")
    col3 = literal_column("col3")
    
    # Test AND
    s = select(and_(col1 == 1, col2 == 2))
    compiled = s.compile(dialect=dialect)
    assert "and" in str(compiled).lower()
    
    # Test OR
    s = select(or_(col1 == 1, col2 == 2))
    compiled = s.compile(dialect=dialect)
    assert "or" in str(compiled).lower()
    
    # Test NOT (SQLAlchemy optimizes not_(col == 1) to col != 1)
    s = select(~(col1 == 1))  # Use bitwise NOT which compiles to NOT
    compiled = s.compile(dialect=dialect)
    # Accept either NOT or != as valid compilation
    compiled_str = str(compiled).lower()
    assert "not" in compiled_str or "!=" in compiled_str
    
    # Test complex boolean expression
    s = select(and_(or_(col1 == 1, col2 == 2), ~(col3 == 3)))
    compiled = s.compile(dialect=dialect)
    compiled_str = str(compiled).lower()
    assert "and" in compiled_str and "or" in compiled_str


def test_subquery_expressions(stub_redshift_dialect):
    """Test subquery compilation"""
    dialect = stub_redshift_dialect
    
    # Create mock table for subquery
    metadata = MetaData()
    table = Table('test_table', metadata,
                  Column('id', Integer),
                  Column('name', String))
    
    # Test EXISTS
    subq = select(table.c.id).where(table.c.name == "test")
    s = select(literal_column("1")).where(subq.exists())
    compiled = s.compile(dialect=dialect)
    assert "EXISTS" in str(compiled)
    
    # Test IN with subquery
    s = select(literal_column("col")).where(literal_column("col").in_(subq))
    compiled = s.compile(dialect=dialect)
    assert "IN" in str(compiled)


def test_limit_offset_compilation(stub_redshift_dialect):
    """Test LIMIT/OFFSET compilation using public API"""
    dialect = stub_redshift_dialect
    
    # Test LIMIT only
    s = select(literal_column("col")).limit(10)
    compiled = s.compile(dialect=dialect)
    assert "LIMIT" in str(compiled)
    
    # Test OFFSET only (should add LIMIT ALL)
    s = select(literal_column("col")).offset(5)
    compiled = s.compile(dialect=dialect)
    assert "LIMIT ALL" in str(compiled) and "OFFSET" in str(compiled)
    
    # Test LIMIT and OFFSET
    s = select(literal_column("col")).limit(10).offset(5)
    compiled = s.compile(dialect=dialect)
    assert "LIMIT" in str(compiled) and "OFFSET" in str(compiled)


def test_parameter_binding(stub_redshift_dialect):
    """Test parameter binding compilation"""
    dialect = stub_redshift_dialect
    
    # Test named parameters
    s = select(literal_column("col")).where(literal_column("col") == bindparam("param1"))
    compiled = s.compile(dialect=dialect)
    # Should use format style for redshift_connector
    assert "%(param1)s" in str(compiled) or ":param1" in str(compiled)
    
    # Test auto-generated parameters (SQLAlchemy generates param names automatically)
    s = select(literal_column("col")).where(literal_column("col") == bindparam(None))
    compiled = s.compile(dialect=dialect)
    # SQLAlchemy auto-generates parameter names like %(param_1)s
    compiled_str = str(compiled)
    assert "%" in compiled_str and "s" in compiled_str  # Format-style parameters


def test_redshift_specific_syntax(stub_redshift_dialect):
    """Test Redshift-specific SQL syntax"""
    dialect = stub_redshift_dialect
    
    # Test DISTKEY in column (this would be in DDL, but test compilation)
    # This is more of a DDL test, but ensure compiler handles it
    
    # Test ENCODE syntax (also DDL)
    # These are tested in DDL tests, but ensure no compilation errors
    
    # Test Redshift-specific functions that might have special compilation
    s = select(func.CONVERT_TIMEZONE("UTC", "PST", func.SYSDATE()))
    compiled = s.compile(dialect=dialect)
    assert "CONVERT_TIMEZONE" in str(compiled)
    
    # Test HLL functions
    s = select(func.HLL_CREATE_SKETCH(literal_column("col")))
    compiled = s.compile(dialect=dialect)
    assert "HLL_CREATE_SKETCH" in str(compiled)


@pytest.mark.parametrize("dialect_cls", [
    RedshiftDialect_psycopg2, 
    RedshiftDialect_psycopg2cffi,
    RedshiftDialect_redshift_connector
])
class TestCompilerDriverParity:
    """Test compiler behavior is consistent across all drivers"""
    
    def test_offset_only_limit_all_all_drivers(self, dialect_cls):
        """Test OFFSET-only queries emit LIMIT ALL for ALL drivers"""
        dialect = dialect_cls()
        
        stmt = select(literal_column("col")).offset(10)
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        assert "LIMIT ALL" in sql, f"LIMIT ALL missing for {dialect_cls.__name__}"
        assert "OFFSET" in sql, f"OFFSET missing for {dialect_cls.__name__}"
    
    def test_limit_with_offset_all_drivers(self, dialect_cls):
        """Test LIMIT+OFFSET queries work correctly for all drivers"""
        dialect = dialect_cls()
        
        stmt = select(literal_column("col")).limit(5).offset(10)
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        assert "LIMIT" in sql, f"LIMIT missing for {dialect_cls.__name__}"
        assert "OFFSET" in sql, f"OFFSET missing for {dialect_cls.__name__}"
        assert "LIMIT ALL" not in sql, f"Unexpected LIMIT ALL for {dialect_cls.__name__}"
    
    def test_basic_select_compilation(self, dialect_cls):
        """Test basic SELECT compilation across drivers"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table("test", meta, 
            Column("id", Integer),
            Column("name", String(50))
        )
        
        stmt = select(table.c.id, table.c.name).where(table.c.id > 10)
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        assert "SELECT" in sql
        assert "test.id" in sql or "test.name" in sql
        assert "WHERE" in sql
    
    def test_join_compilation(self, dialect_cls):
        """Test JOIN compilation across drivers"""
        dialect = dialect_cls()
        meta = MetaData()
        table1 = Table("table1", meta, Column("id", Integer))
        table2 = Table("table2", meta, Column("id", Integer), Column("table1_id", Integer))
        
        stmt = select(table1.c.id, table2.c.id).select_from(
            table1.join(table2, table1.c.id == table2.c.table1_id)
        )
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        assert "JOIN" in sql
        assert "table1" in sql
        assert "table2" in sql
    
    def test_subquery_compilation(self, dialect_cls):
        """Test subquery compilation across drivers"""
        dialect = dialect_cls()
        meta = MetaData()
        table = Table("test", meta, Column("id", Integer), Column("value", Integer))
        
        subq = select(table.c.id).where(table.c.value > 100).subquery()
        stmt = select(subq.c.id)
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        assert "SELECT" in sql
        assert "FROM" in sql
        # Should have nested SELECT
        assert sql.count("SELECT") >= 2
    
    def test_parameter_style_consistency(self, dialect_cls):
        """Test parameter binding style is consistent per driver"""
        dialect = dialect_cls()
        
        stmt = select(literal_column("col")).where(literal_column("col") == bindparam("test_param"))
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        # redshift_connector uses format style, psycopg2 uses pyformat
        if "redshift_connector" in dialect_cls.__name__:
            assert "%(test_param)s" in sql or "%s" in sql
        else:
            assert "%(test_param)s" in sql  # psycopg2 also uses pyformat
    
    def test_function_compilation_consistency(self, dialect_cls):
        """Test function compilation is consistent across drivers"""
        dialect = dialect_cls()
        
        # Test NOW() -> SYSDATE conversion
        stmt = select(func.NOW())
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        assert "SYSDATE" in sql
        
        # Test other Redshift functions
        stmt = select(func.GETDATE())
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        assert "getdate" in sql.lower()
    
    def test_delete_using_compilation(self, dialect_cls):
        """Test DELETE ... USING compilation across drivers"""
        dialect = dialect_cls()
        meta = MetaData()
        table1 = Table("table1", meta, Column("id", Integer))
        table2 = Table("table2", meta, Column("id", Integer))
        
        # This tests the custom DELETE compilation in dialect.py
        from sqlalchemy import delete
        stmt = delete(table1).where(table1.c.id == table2.c.id)
        compiled = stmt.compile(dialect=dialect)
        sql = str(compiled)
        
        assert "DELETE FROM" in sql
        assert "USING" in sql  # Redshift-specific DELETE ... USING syntax
        assert "table1" in sql
        assert "table2" in sql
