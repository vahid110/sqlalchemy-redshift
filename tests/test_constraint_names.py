import pytest


def test_pk_name(redshift_session):
    dialect = redshift_session.bind.dialect
    pk = dialect.get_pk_constraint(
        redshift_session.connection(),
        "reflection_named_pk_constraint"
    )
    assert pk['name'] == "reflection_named_pk_constraint__pkey"
    assert pk['constrained_columns'] == ["col1", "col2"]


@pytest.mark.xfail(reason="redshift_connector returns 'public' instead of None for referred_schema")
def test_fk_name(redshift_session):
    # Skip for psycopg2 if needed
    if 'psycopg2' in str(redshift_session.bind.dialect.driver):
        # psycopg2 works fine for this test
        pass
    
    dialect = redshift_session.bind.dialect
    fks = dialect.get_foreign_keys(
        redshift_session.connection(),
        "reflection_named_fk_constraint"
    )
    assert len(fks) == 1
    assert fks[0]["name"] == "reflection_named_fk_constraint__fk"
    assert fks[0]["constrained_columns"] == ["col1"]
    assert fks[0]["referred_columns"] == ["col1"]
    assert fks[0]["referred_schema"] is None
    assert fks[0]["referred_table"] == "reflection_unique_constraint"
