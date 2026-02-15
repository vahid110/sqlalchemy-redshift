"""SQLAlchemy Compliance Test Suite Integration

Integrates SQLAlchemy's official test suite to validate dialect compliance.

Run with:
    pytest tests/sqlalchemy_compliance/test_suite.py -v
"""

from . import provision  # noqa: F401
from sqlalchemy.testing.suite import *  # noqa: F401, F403

# Explicitly exclude tests for unsupported features
del UuidTest  # Redshift doesn't support UUID type
