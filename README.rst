sqlalchemy-redshift
===================

.. image:: https://img.shields.io/pypi/v/sqlalchemy-redshift.svg
    :target: https://pypi.org/project/sqlalchemy-redshift/
    :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/sqlalchemy-redshift.svg
    :target: https://pypi.org/project/sqlalchemy-redshift/
    :alt: Python Versions

.. image:: https://img.shields.io/badge/SQLAlchemy-1.4%20%7C%202.0-blue.svg
    :target: https://sqlalchemy.org/
    :alt: SQLAlchemy Versions

Amazon Redshift dialect for SQLAlchemy.

**Production-ready SQLAlchemy 2.0 support with 1.4 backward compatibility.**

Features
--------

* **SQLAlchemy 2.0 & 1.4 Support**: Full compatibility with both SQLAlchemy versions
* **Multiple Drivers**: Support for ``redshift_connector``, ``psycopg2``, and ``psycopg2cffi``
* **Redshift-Specific Types**: ``SUPER``, ``GEOMETRY``, ``TIMESTAMPTZ``, ``JSON``, arrays
* **DDL Extensions**: ``DISTSTYLE``, ``DISTKEY``, ``SORTKEY``, ``IDENTITY`` columns
* **COPY/UNLOAD Commands**: Native support for bulk data operations
* **Authentication**: 9 authentication methods including IAM, SAML, Azure AD
* **Production Features**: Connection pooling, error handling, performance optimization

Installation
------------

The package is available on PyPI::

    pip install sqlalchemy-redshift

.. warning::

    This dialect requires either ``redshift_connector`` or ``psycopg2``
    to work properly. It does not provide
    it as required, but relies on you to select the distribution you need:

    * psycopg2 - standard distribution of psycopg2, requires compilation so few system dependencies are required for it
    * psycopg2-binary - already compiled distribution (no system dependencies are required)
    * psycopg2cffi - pypy compatible version

    See `Psycopg2's binary install docs <http://initd.org/psycopg/docs/install.html#binary-install-from-pypi>`_
    for more context on choosing a distribution.

Usage
-----

Basic Connection
~~~~~~~~~~~~~~~~

The DSN format is similar to that of regular Postgres::

    >>> import sqlalchemy as sa
    >>> sa.create_engine('redshift+psycopg2://username@host.amazonaws.com:5439/database')
    Engine(redshift+psycopg2://username@host.amazonaws.com:5439/database)

Driver Selection
~~~~~~~~~~~~~~~~

Choose the appropriate driver for your needs:

* **redshift_connector** (recommended): Official AWS driver with advanced features::

    sa.create_engine('redshift+redshift_connector://user@cluster.region.redshift.amazonaws.com:5439/dev')

* **psycopg2**: Standard PostgreSQL driver::

    sa.create_engine('redshift+psycopg2://user:pass@cluster.region.redshift.amazonaws.com:5439/dev')

* **psycopg2cffi**: PyPy-compatible driver::

    sa.create_engine('redshift+psycopg2cffi://user:pass@cluster.region.redshift.amazonaws.com:5439/dev')

Authentication Methods
~~~~~~~~~~~~~~~~~~~~~~

**Password Authentication**::

    redshift+redshift_connector://user:password@cluster:5439/database

**IAM Authentication**::

    redshift+redshift_connector://user@cluster:5439/database?iam=true&aws_profile=default

**IAM Role Authentication**::

    redshift+redshift_connector://user@cluster:5439/database?iam=true&role_arn=arn:aws:iam::123456789012:role/RedshiftRole

**SAML/Browser IdP**::

    redshift+redshift_connector://user@cluster:5439/database?plugin_name=browser_idp&client_id=your_client_id

**Azure AD**::

    redshift+redshift_connector://user@cluster:5439/database?plugin_name=azure_browser_idp&client_id=your_client_id

Redshift-Specific Features
~~~~~~~~~~~~~~~~~~~~~~~~~~

**DDL with Distribution and Sort Keys**::

    >>> from sqlalchemy import Table, Column, Integer, String, MetaData
    >>> metadata = MetaData()
    >>> users = Table('users', metadata,
    ...     Column('id', Integer, primary_key=True),
    ...     Column('name', String(50)),
    ...     Column('email', String(100)),
    ...     redshift_diststyle='KEY',
    ...     redshift_distkey='id',
    ...     redshift_sortkey=['id', 'name']
    ... )

**COPY Command for Bulk Loading**::

    >>> from sqlalchemy_redshift import CopyCommand
    >>> copy_cmd = CopyCommand(
    ...     table=users,
    ...     data_location='s3://bucket/data.csv',
    ...     format='CSV',
    ...     compression='GZIP'
    ... )
    >>> engine.execute(copy_cmd)

**UNLOAD Command for Data Export**::

    >>> from sqlalchemy_redshift import UnloadFromSelect
    >>> from sqlalchemy import select
    >>> unload_cmd = UnloadFromSelect(
    ...     select=select([users]),
    ...     unload_location='s3://bucket/export/',
    ...     format='PARQUET'
    ... )
    >>> engine.execute(unload_cmd)

**SUPER/JSON Type Handling**::

    >>> from sqlalchemy_redshift import SUPER
    >>> events = Table('events', metadata,
    ...     Column('id', Integer, primary_key=True),
    ...     Column('data', SUPER)  # Stores JSON data
    ... )

Feature Support Matrix
~~~~~~~~~~~~~~~~~~~~~~

+------------------------+----------+----------+----------+
| Feature                | psycopg2 | psycopg2 | redshift |
|                        |          | cffi     | connector|
+========================+==========+==========+==========+
| Basic SQL Operations   | ✓        | ✓        | ✓        |
+------------------------+----------+----------+----------+
| DDL (DIST/SORT keys)   | ✓        | ✓        | ✓        |
+------------------------+----------+----------+----------+
| COPY/UNLOAD Commands   | ✓        | ✓        | ✓        |
+------------------------+----------+----------+----------+
| SUPER/JSON Types       | ✓        | ✓        | ✓        |
+------------------------+----------+----------+----------+
| Reflection/Inspection  | ✓        | ✓        | ✓        |
+------------------------+----------+----------+----------+
| Statement Caching      | ✗        | ✗        | ✓        |
+------------------------+----------+----------+----------+
| IAM Authentication    | ✗        | ✗        | ✓        |
+------------------------+----------+----------+----------+
| SAML/Browser IdP       | ✗        | ✗        | ✓        |
+------------------------+----------+----------+----------+
| Connection Health      | Basic    | Basic    | Advanced |
+------------------------+----------+----------+----------+

Migrating from SQLAlchemy 1.x to 2.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Core API Changes**:

.. code-block:: python

    # SQLAlchemy 1.x style
    result = engine.execute("SELECT * FROM users")
    
    # SQLAlchemy 2.0 style (recommended)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM users"))

**Query Construction**:

.. code-block:: python

    # SQLAlchemy 1.x style
    query = select([users.c.id, users.c.name])
    
    # SQLAlchemy 2.0 style (recommended)
    query = select(users.c.id, users.c.name)

**Important Notes**:

* Redshift does **not** support ``RETURNING`` clauses
* ``COPY`` and ``UNLOAD`` commands require ``isolation_level="AUTOCOMMIT"``
* Use ``use_insertmanyvalues=True`` for optimized bulk inserts

See the `RedshiftDDLCompiler documentation
<https://sqlalchemy-redshift.readthedocs.org/en/latest/ddl-compiler.html>`_
for details on Redshift-specific features the dialect supports.

Running Tests
-------------

Local Testing
~~~~~~~~~~~~~

Tests are run via tox with comprehensive driver and SQLAlchemy version matrix::

    $ tox

This runs 20 test environments covering:

* Python 3.8-3.12
* SQLAlchemy 1.4.x and 2.0.x  
* psycopg2 and redshift_connector drivers

Specific environment examples::

    $ tox -e py311-sa20-redshift_connector  # Python 3.11 + SA 2.0 + redshift_connector
    $ tox -e py39-sa14-psycopg2             # Python 3.9 + SA 1.4 + psycopg2

Real Cluster Testing
~~~~~~~~~~~~~~~~~~~~

Optional integration tests against real Redshift clusters require environment variables:

* ``REDSHIFT_TEST_HOST`` - Cluster endpoint
* ``REDSHIFT_TEST_DATABASE`` - Database name
* ``REDSHIFT_TEST_USER`` - Username
* ``REDSHIFT_TEST_PASSWORD`` - Password (or use IAM)
* ``REDSHIFT_TEST_S3_BUCKET`` - S3 bucket for COPY/UNLOAD tests (optional)

Example::

    export REDSHIFT_TEST_HOST="my-cluster.abc123.us-east-1.redshift.amazonaws.com"
    export REDSHIFT_TEST_DATABASE="dev"
    export REDSHIFT_TEST_USER="testuser"
    export REDSHIFT_TEST_PASSWORD="mypassword"
    export REDSHIFT_TEST_S3_BUCKET="my-test-bucket"
    
    # Run tests including real cluster smoke tests
    tox -e py311-sa20-redshift_connector

**Warning**: Practice caution when running integration tests against production instances.
These tests create and drop temporary tables and may affect cluster performance.

Continuous Integration (CI)
---------------------------

Project CI is built using AWS CodePipeline and CloudFormation. Please see the ``ci/`` folder and included ``README.txt``
for details on how to spin up the project's CI.

Releasing
---------

To perform a release, you will need to be an admin for the project on
GitHub and on PyPI. Contact the maintainers if you need that access.

You will need to have a `~/.pypirc` with your PyPI credentials and
also the following settings::

    [zest.releaser]
    create-wheels = yes

To perform a release, run the following::

    python -m venv ~/.virtualenvs/dist
    workon dist
    pip install -U pip setuptools wheel
    pip install -U tox zest.releaser
    fullrelease  # follow prompts, use semver ish with versions.

The releaser will handle updating version data on the package and in
CHANGES.rst along with tagging the repo and uploading to PyPI.

Compatibility
-------------

**SQLAlchemy Versions**:

* SQLAlchemy 2.0.x (recommended)
* SQLAlchemy 1.4.48+ (backward compatibility)

**Python Versions**:

* Python 3.8+
* PyPy 3.8+ (with psycopg2cffi)

**Redshift Features**:

* All Redshift cluster types (dc2, ds2, ra3)
* Redshift Serverless
* Redshift Spectrum (external tables)
* Redshift ML integration

Contributing
------------

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: ``tox``
5. Submit a pull request

For major changes, please open an issue first to discuss the proposed changes.

License
-------

This project is licensed under the MIT License - see the LICENSE file for details.
