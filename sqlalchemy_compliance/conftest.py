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
