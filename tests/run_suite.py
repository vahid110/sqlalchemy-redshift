"""
SQLAlchemy Compliance Test Suite Runner

Run SQLAlchemy's official test suite against Redshift dialect.

Usage:
    python tests/run_suite.py
"""

import sys
from sqlalchemy.testing import runner

# Configure for Redshift
sys.argv = [
    'pytest',
    '--db', 'redshift+psycopg2://username:password@your-cluster.region.redshift.amazonaws.com:5439/dev',
    '-v',
    '--tb=short',
    'sqlalchemy.testing.suite'
]

if __name__ == '__main__':
    runner.main()
