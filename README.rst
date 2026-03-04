sqlalchemy-redshift
===================

Amazon Redshift dialect for SQLAlchemy.

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

**Recommended: Use redshift_connector (native AWS driver)**

For SQLAlchemy 2.0+, we strongly recommend using the ``redshift_connector`` driver::

    >>> import sqlalchemy as sa
    >>> sa.create_engine('redshift+redshift_connector://username:password@host.amazonaws.com:5439/database')
    Engine(redshift+redshift_connector://username:password@host.amazonaws.com:5439/database)

The ``redshift_connector`` dialect provides:

* Full SQLAlchemy 2.0 compatibility
* Native Redshift API support for reflection (get_tables, get_columns, etc.)
* Better performance and reliability
* Active maintenance by AWS

**Legacy: psycopg2 dialects (limited SA 2.0 support)**

The psycopg2-based dialects are maintained for backward compatibility but have limitations with SQLAlchemy 2.0::

    >>> sa.create_engine('redshift+psycopg2://username@host.amazonaws.com:5439/database')
    Engine(redshift+psycopg2://username@host.amazonaws.com:5439/database)

.. warning::

    The ``psycopg2`` and ``psycopg2cffi`` dialects inherit from PostgreSQL's dialect,
    which queries system columns that don't exist in Redshift (based on PostgreSQL 8.0.2).
    This causes reflection failures with SQLAlchemy 2.0+. 
    
    **We recommend migrating to redshift_connector for new projects.**

The DSN format is similar to that of regular Postgres::

    >>> import sqlalchemy as sa
    >>> # Recommended for SA 2.0+
    >>> sa.create_engine('redshift+redshift_connector://username:password@host.amazonaws.com:5439/database')
    Engine(redshift+redshift_connector://username:password@host.amazonaws.com:5439/database)
    >>> # Legacy (limited SA 2.0 support)
    >>> sa.create_engine('redshift+psycopg2://username@host.amazonaws.com:5439/database')
    Engine(redshift+psycopg2://username@host.amazonaws.com:5439/database)

See the `RedshiftDDLCompiler documentation
<https://sqlalchemy-redshift.readthedocs.org/en/latest/ddl-compiler.html>`_
for details on Redshift-specific features the dialect supports.

Running Tests
-------------
Tests are ran via tox and can be run with the following command::

    $ tox

However, this will not run integration tests unless the following
environment variables are set:

* REDSHIFT_HOST
* REDSHIFT_PORT
* REDSHIFT_USERNAME
* PGPASSWORD (this is the redshift instance password)
* REDSHIFT_DATABASE
* REDSHIFT_IAM_ROLE_ARN

Note that the IAM role specified will need to be associated with
redshift cluster and have the correct permissions to create databases
and tables as well drop them. Exporting these environment variables in
your shell and running ``tox`` will run the integration tests against
a real redshift instance. Practice caution when running these tests
against a production instance.

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
