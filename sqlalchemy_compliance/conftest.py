"""SQLAlchemy test suite configuration."""

import pytest
from sqlalchemy.testing.plugin.pytestplugin import *  # noqa: F401, F403

# Import Redshift-specific provisioning
from . import provision  # noqa: F401


def pytest_collection_modifyitems(config, items):
    """Skip specific test parameters that test unsupported Redshift features."""
    for item in items:
        nodeid = item.nodeid
        
        # Skip FOR UPDATE tests - Redshift doesn't support row-level locking
        if "ServerSideCursorsTest" in nodeid and "test_ss_cursor_status" in nodeid:
            if "[for_update_expr]" in nodeid or "[for_update_string]" in nodeid:
                item.add_marker(pytest.mark.skip(
                    reason="Redshift doesn't support SELECT FOR UPDATE"
                ))
        
        # Skip autoincrement roundtrip tests - Redshift uses IDENTITY not sequences
        if "ServerSideCursorsTest" in nodeid:
            if "test_roundtrip_fetchall" in nodeid or "test_roundtrip_fetchmany" in nodeid:
                item.add_marker(pytest.mark.skip(
                    reason="Redshift uses IDENTITY columns, not sequences for autoincrement"
                ))
        
        # Skip test_no_results_for_non_returning_insert - Redshift IDENTITY requires DEFAULT
        if "InsertBehaviorTest" in nodeid and "test_no_results_for_non_returning_insert" in nodeid:
            item.add_marker(pytest.mark.skip(
                reason="Redshift IDENTITY columns require DEFAULT keyword when not providing explicit values"
            ))
        
        # Skip test_insert_from_select_autoinc - INSERT...SELECT doesn't auto-populate IDENTITY
        if "InsertBehaviorTest" in nodeid and "test_insert_from_select_autoinc" in nodeid:
            if "no_rows" not in nodeid:  # Keep test_insert_from_select_autoinc_no_rows
                item.add_marker(pytest.mark.skip(
                    reason="Redshift INSERT...SELECT doesn't auto-populate IDENTITY columns"
                ))
        
        # Skip empty_insert tests - Redshift doesn't support INSERT with no values
        if "InsertBehaviorTest" in nodeid:
            if "test_empty_insert" in nodeid:
                item.add_marker(pytest.mark.skip(
                    reason="Redshift doesn't support empty INSERT (requires DEFAULT for IDENTITY columns)"
                ))
