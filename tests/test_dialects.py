import pytest

from sqlalchemy.dialects.postgresql import (
    psycopg2, psycopg2cffi
)
from sqlalchemy.dialects.postgresql.base import PGDialect

from redshift_sqlalchemy import dialect
from rs_sqla_test_utils.utils import make_mock_engine


@pytest.mark.parametrize('name, expected_dialect', [
    ('redshift', psycopg2.dialect),
    ('redshift+psycopg2', psycopg2.dialect),
    ('redshift+psycopg2cffi', psycopg2cffi.dialect),
    ('redshift+redshift_connector', PGDialect),
])
def test_dialect_inherits_from_sqlalchemy_dialect(name, expected_dialect):
    engine = make_mock_engine(name)

    assert isinstance(engine.dialect, expected_dialect)


@pytest.mark.parametrize('name, expected_dialect', [
    ('redshift', dialect.Psycopg2RedshiftDialectMixin),
    ('redshift+psycopg2', dialect.Psycopg2RedshiftDialectMixin),
    ('redshift+psycopg2cffi', dialect.Psycopg2RedshiftDialectMixin),
])
def test_dialect_inherits_from_redshift_mixin(name, expected_dialect):
    engine = make_mock_engine(name)

    assert isinstance(engine.dialect, expected_dialect)


@pytest.mark.parametrize('name, expected_dialect', [
    ('redshift', dialect.RedshiftDialect_psycopg2),
    ('redshift+psycopg2', dialect.RedshiftDialect_psycopg2),
    ('redshift+psycopg2cffi', dialect.RedshiftDialect_psycopg2cffi),
])
def test_dialect_registered_correct_class(name, expected_dialect):
    engine = make_mock_engine(name)

    assert isinstance(engine.dialect, expected_dialect)


def test_redshift_dialect_synonym_of_redshift_dialect_psycopg2():
    assert isinstance(
        dialect.RedshiftDialect(),
        dialect.RedshiftDialect_psycopg2
    )


class TestStatementCache:
    """Test statement caching behavior per driver"""
    
    def test_statement_cache_flags(self):
        """Verify statement cache flags are set correctly per driver"""
        from sqlalchemy_redshift.dialect import (
            RedshiftDialect_psycopg2, 
            RedshiftDialect_psycopg2cffi,
            RedshiftDialect_redshift_connector
        )
        
        # redshift_connector should support statement cache
        rc_dialect = RedshiftDialect_redshift_connector()
        assert rc_dialect.supports_statement_cache is True
        
        # psycopg2 drivers should not support statement cache
        pg2_dialect = RedshiftDialect_psycopg2()
        assert pg2_dialect.supports_statement_cache is False
        
        pg2cffi_dialect = RedshiftDialect_psycopg2cffi()
        assert pg2cffi_dialect.supports_statement_cache is False


class TestFeatureFlagConsistency:
    """Test that all drivers inherit the same Redshift-specific flags"""
    
    def test_redshift_flags_inherited(self):
        """Verify all drivers inherit critical Redshift flags from mixin"""
        from sqlalchemy_redshift.dialect import (
            RedshiftDialect_psycopg2, 
            RedshiftDialect_psycopg2cffi,
            RedshiftDialect_redshift_connector
        )
        
        dialects = [
            RedshiftDialect_psycopg2(),
            RedshiftDialect_psycopg2cffi(),
            RedshiftDialect_redshift_connector()
        ]
        
        for dialect in dialects:
            # Critical Redshift flags that must be consistent
            assert dialect.insert_returning is False, f"insert_returning should be False for {type(dialect)}"
            assert dialect.use_insertmanyvalues is True, f"use_insertmanyvalues should be True for {type(dialect)}"
            assert dialect.supports_sane_rowcount is False, f"supports_sane_rowcount should be False for {type(dialect)}"


class TestEntryPoints:
    """Test that dialect entry points are properly registered"""
    
    def test_entry_points_loadable(self):
        """Test that all entry points can be loaded"""
        from sqlalchemy.dialects import registry
        
        # Test main redshift entry point
        redshift_dialect = registry.load("redshift")
        assert redshift_dialect is not None
        
        # Test specific driver entry points
        psycopg2_dialect = registry.load("redshift.psycopg2")
        assert psycopg2_dialect is not None
        
        psycopg2cffi_dialect = registry.load("redshift.psycopg2cffi")
        assert psycopg2cffi_dialect is not None
        
        connector_dialect = registry.load("redshift.redshift_connector")
        assert connector_dialect is not None
