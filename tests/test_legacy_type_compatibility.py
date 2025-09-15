"""
Tests for compatibility with existing/legacy Redshift types
Ensures existing functionality continues to work as expected
"""
import pytest
import sqlalchemy as sa
from sqlalchemy import MetaData, Table, Column, Integer, String
from sqlalchemy.engine import create_mock_engine

from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector
from sqlalchemy_redshift import dialect


class TestExistingRedshiftTypes:
    """Test that existing Redshift types continue to work"""
    
    def test_existing_types_available(self):
        """Test that all existing types are still available"""
        existing_types = [
            'GEOMETRY', 'SUPER', 'TIMESTAMPTZ', 'TIMETZ', 'HLLSKETCH'
        ]
        
        for type_name in existing_types:
            assert hasattr(dialect, type_name), f"Missing type: {type_name}"

    def test_geometry_type_compatibility(self):
        """Test GEOMETRY type compatibility"""
        geometry_type = dialect.GEOMETRY()
        assert geometry_type.__visit_name__ == "GEOMETRY"
        
        # Test compilation
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        assert type_compiler.visit_GEOMETRY(geometry_type) == "GEOMETRY"

    def test_super_type_compatibility(self):
        """Test SUPER type compatibility"""
        super_type = dialect.SUPER()
        assert super_type.__visit_name__ == "SUPER"
        
        # Test compilation
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        assert type_compiler.visit_SUPER(super_type) == "SUPER"

    def test_timestamptz_type_compatibility(self):
        """Test TIMESTAMPTZ type compatibility"""
        timestamptz_type = dialect.TIMESTAMPTZ()
        assert timestamptz_type.__visit_name__ == "TIMESTAMPTZ"
        
        # Test compilation
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        assert type_compiler.visit_TIMESTAMPTZ(timestamptz_type) == "TIMESTAMPTZ"

    def test_timetz_type_compatibility(self):
        """Test TIMETZ type compatibility"""
        timetz_type = dialect.TIMETZ()
        assert timetz_type.__visit_name__ == "TIMETZ"
        
        # Test compilation
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        assert type_compiler.visit_TIMETZ(timetz_type) == "TIMETZ"

    def test_hllsketch_type_compatibility(self):
        """Test HLLSKETCH type compatibility"""
        hllsketch_type = dialect.HLLSKETCH()
        assert hllsketch_type.__visit_name__ == "HLLSKETCH"
        
        # Test compilation
        redshift_dialect = RedshiftDialect_redshift_connector()
        type_compiler = redshift_dialect.type_compiler
        assert type_compiler.visit_HLLSKETCH(hllsketch_type) == "HLLSKETCH"


class TestLegacyTypeRegistration:
    """Test that legacy types are properly registered"""
    
    def test_existing_ischema_names(self):
        """Test that existing ischema names are preserved"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        ischema_names = redshift_dialect.ischema_names
        
        # Check that existing types are still registered
        expected_mappings = {
            'geometry': dialect.GEOMETRY,
            'super': dialect.SUPER,
            'time with time zone': dialect.TIMETZ,
            'timestamp with time zone': dialect.TIMESTAMPTZ,
            'hllsketch': dialect.HLLSKETCH,
        }
        
        for schema_name, expected_type in expected_mappings.items():
            assert schema_name in ischema_names, f"Missing schema name: {schema_name}"
            assert ischema_names[schema_name] == expected_type, f"Wrong type for {schema_name}"

    def test_all_types_in_module_exports(self):
        """Test that all types are properly exported in __all__"""
        from sqlalchemy_redshift.dialect import __all__
        
        expected_types = [
            'GEOMETRY', 'SUPER', 'TIMESTAMPTZ', 'TIMETZ', 'HLLSKETCH',
            'ABSTIME', 'INTERVAL', 'JSON', 'RedshiftArray'
        ]
        
        for type_name in expected_types:
            assert type_name in __all__, f"Type {type_name} not in __all__"


class TestLegacyDDLGeneration:
    """Test DDL generation with legacy types"""
    
    def test_legacy_types_ddl_generation(self):
        """Test DDL generation with existing types"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        legacy_table = Table(
            'legacy_types_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String),
            Column('geometry_col', dialect.GEOMETRY()),
            Column('super_col', dialect.SUPER()),
            Column('timestamp_col', dialect.TIMESTAMPTZ()),
            Column('time_col', dialect.TIMETZ()),
            Column('hll_col', dialect.HLLSKETCH()),
        )
        
        # Generate DDL
        ddl = str(sa.schema.CreateTable(legacy_table).compile(engine))
        
        # Verify existing types still work in DDL
        assert 'GEOMETRY' in ddl
        assert 'SUPER' in ddl
        assert 'TIMESTAMPTZ' in ddl
        assert 'TIMETZ' in ddl
        assert 'HLLSKETCH' in ddl

    def test_mixed_legacy_and_new_types(self):
        """Test DDL generation with both legacy and new types"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        mixed_table = Table(
            'mixed_types_test',
            metadata,
            Column('id', Integer, primary_key=True),
            # Legacy types
            Column('geometry_col', dialect.GEOMETRY()),
            Column('super_col', dialect.SUPER()),
            Column('timestamptz_col', dialect.TIMESTAMPTZ()),
            # New types
            Column('abstime_col', dialect.ABSTIME()),
            Column('interval_col', dialect.INTERVAL()),
            Column('json_col', dialect.JSON()),
            Column('array_col', dialect.RedshiftArray(String)),
        )
        
        # Generate DDL
        ddl = str(sa.schema.CreateTable(mixed_table).compile(engine))
        
        # Verify all types work together
        assert 'mixed_types_test' in ddl
        # Legacy types
        assert 'GEOMETRY' in ddl
        assert 'SUPER' in ddl
        assert 'TIMESTAMPTZ' in ddl
        # New types
        assert 'ABSTIME' in ddl
        assert 'INTERVAL' in ddl
        # JSON maps to SUPER, so we already have SUPER above


class TestDialectCompatibility:
    """Test dialect-level compatibility"""
    
    def test_dialect_properties_preserved(self):
        """Test that existing dialect properties are preserved"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Test that existing properties are preserved
        assert redshift_dialect.name == 'redshift'
        assert redshift_dialect.max_identifier_length == 127
        assert redshift_dialect.driver == 'redshift_connector'

    def test_dialect_methods_preserved(self):
        """Test that existing dialect methods are available"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Test that existing methods are available
        required_methods = [
            'get_columns', 'get_table_names', 'get_view_names', 'has_table',
            'get_pk_constraint', 'get_foreign_keys', 'get_unique_constraints',
            'get_table_options', 'get_view_definition', 'get_indexes'
        ]
        
        for method_name in required_methods:
            assert hasattr(redshift_dialect, method_name), f"Missing method: {method_name}"
            assert callable(getattr(redshift_dialect, method_name)), f"Method not callable: {method_name}"

    def test_compiler_classes_preserved(self):
        """Test that compiler classes are preserved"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Verify compiler classes
        assert redshift_dialect.statement_compiler is not None
        assert redshift_dialect.ddl_compiler is not None
        assert redshift_dialect.type_compiler is not None
        assert redshift_dialect.preparer is not None

    def test_dialect_inheritance_preserved(self):
        """Test that dialect maintains proper inheritance"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Should inherit from proper base classes
        from sqlalchemy.dialects.postgresql.base import PGDialect
        from sqlalchemy_redshift.dialect import RedshiftDialectMixin
        
        assert isinstance(redshift_dialect, PGDialect)
        assert isinstance(redshift_dialect, RedshiftDialectMixin)


class TestQueryGeneration:
    """Test query generation with legacy types"""
    
    def test_select_queries_with_legacy_types(self):
        """Test SELECT queries with legacy types"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'query_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('geometry_data', dialect.GEOMETRY()),
            Column('super_data', dialect.SUPER()),
        )
        
        # Test query generation
        select_query = sa.select(table.c.id, table.c.geometry_data, table.c.super_data)
        query_sql = str(select_query.compile(engine))
        
        assert 'SELECT' in query_sql
        assert 'query_test.id' in query_sql
        assert 'query_test.geometry_data' in query_sql
        assert 'query_test.super_data' in query_sql

    def test_insert_queries_with_legacy_types(self):
        """Test INSERT queries with legacy types"""
        engine = create_mock_engine('redshift+redshift_connector://', lambda sql, *_: None)
        
        metadata = MetaData()
        table = Table(
            'insert_test',
            metadata,
            Column('id', Integer, primary_key=True),
            Column('super_data', dialect.SUPER()),
        )
        
        # Test insert query generation
        insert_query = table.insert().values(id=1, super_data='{"key": "value"}')
        query_sql = str(insert_query.compile(engine))
        
        assert 'INSERT INTO insert_test' in query_sql
        assert 'super_data' in query_sql