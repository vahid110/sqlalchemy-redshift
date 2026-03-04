"""
Test configuration and fixtures for sqlalchemy-redshift tests.

Supports loading credentials from:
1. Environment variables (REDSHIFT_TEST_*)
2. INI file (tests/redshift_test.ini)
"""

import os
import copy
import contextlib
import itertools
import uuid
import functools
import configparser
from pathlib import Path
from logging import getLogger

from rs_sqla_test_utils.db import EngineDefinition

import pytest
import sqlalchemy as sa

from rs_sqla_test_utils import db
from rs_sqla_test_utils.utils import make_mock_engine

logger = getLogger(__name__)

_unicode = type(u'')


def load_test_config():
    """Load test configuration from environment or INI file"""
    config = {}
    
    # First try environment variables
    env_vars = [
        'REDSHIFT_TEST_HOST',
        'REDSHIFT_TEST_DATABASE', 
        'REDSHIFT_TEST_USER',
        'REDSHIFT_TEST_PASSWORD',
        'REDSHIFT_TEST_PORT',
        'REDSHIFT_TEST_S3_BUCKET'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            config[var] = value
    
    # If no env vars, try INI file
    if not config:
        ini_path = Path(__file__).parent / 'redshift_test.ini'
        if ini_path.exists():
            parser = configparser.ConfigParser()
            parser.read(ini_path)
            
            if 'redshift' in parser:
                section = parser['redshift']
                config.update({
                    'REDSHIFT_TEST_HOST': section.get('host'),
                    'REDSHIFT_TEST_DATABASE': section.get('database'),
                    'REDSHIFT_TEST_USER': section.get('user'),
                    'REDSHIFT_TEST_PASSWORD': section.get('password'),
                    'REDSHIFT_TEST_PORT': section.get('port', '5439'),
                    'REDSHIFT_TEST_S3_BUCKET': section.get('s3_bucket'),
                    'REDSHIFT_TEST_IAM_ROLE': section.get('iam_role_arn')
                })
    
    # Set environment variables for other modules
    for key, value in config.items():
        if value:
            os.environ[key] = value
    
    return config


# Load config at import time
TEST_CONFIG = load_test_config()


@pytest.fixture(scope="session")
def connection_kwargs(redshift_dialect_flavor):
    """Connection parameters for running integration tests"""
    host = TEST_CONFIG.get('REDSHIFT_TEST_HOST')
    port = TEST_CONFIG.get('REDSHIFT_TEST_PORT', '5439')
    username = TEST_CONFIG.get('REDSHIFT_TEST_USER')
    password = TEST_CONFIG.get('REDSHIFT_TEST_PASSWORD')
    database = TEST_CONFIG.get('REDSHIFT_TEST_DATABASE', 'dev')
    
    if not all([host, username, password]):
        pytest.skip("No database credentials found. Set environment variables or create tests/redshift_test.ini")

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "database": database,
        "dialect": redshift_dialect_flavor,
    }


@pytest.fixture(scope="session")
def iam_role_arn():
    return os.getenv("REDSHIFT_IAM_ROLE_ARN", "arn:aws:iam::000123456789:role/redshiftrole")


@pytest.fixture(scope="session")
def aws_account_id(iam_role_arn):
    try:
        return iam_role_arn.split(":")[4]
    except IndexError:
        pytest.fail("Unable to parse aws_account_id from iam_role_arn")


@pytest.fixture(scope="session")
def iam_role_name(iam_role_arn):
    try:
        return iam_role_arn.split("/")[1]
    except IndexError:
        pytest.fail("Unable to parse iam_role_name from iam_role_arn")


@pytest.fixture(scope="session")
def iam_role_arn_with_aws_partition():
    return os.getenv("REDSHIFT_IAM_ROLE_ARN_WITH_AWS_PARTITION", "arn:aws-us-gov:iam::000123456789:role/redshiftrole")


@pytest.fixture(scope="session")
def aws_partition(iam_role_arn_with_aws_partition):
    try:
        return iam_role_arn_with_aws_partition.split(":")[1]
    except IndexError:
        pytest.fail("Unable to parse aws_partition from iam_role_arn_with_aws_partition")


@pytest.fixture(scope="session")
def iam_role_arns():
    default_arns = "arn:aws:iam::000123456789:role/redshiftrole,arn:aws:iam::000123456789:role/redshiftrole2"
    arns = os.getenv("REDSHIFT_IAM_ROLE_ARNS", default_arns)
    return arns.split(",")


def database_name_generator():
    template = 'testdb_{uuid}_{count}'
    db_uuid = _unicode(uuid.uuid1()).replace('-', '')
    for i in itertools.count():
        yield template.format(uuid=db_uuid, count=i)


database_name = functools.partial(next, database_name_generator())


class DatabaseTool(object):
    def __init__(self, engine_definition: EngineDefinition):
        self.engine_definition = engine_definition
        self.engine = engine_definition.engine()

    def migrate(self, engine):
        from rs_sqla_test_utils import models
        from rs_sqla_test_utils.utils import is_sqlalchemy_2
        
        if is_sqlalchemy_2:
            # SA 2.0: Use connection context
            with engine.begin() as conn:
                models.Base.metadata.create_all(conn)
        else:
            # SA 1.4: Use bind parameter
            models.Base.metadata.create_all(bind=engine)

    @contextlib.contextmanager
    def _database(self):
        from sqlalchemy_redshift.dialect import RedshiftDialect_psycopg2cffi

        db_name = database_name()
        opts = {"isolation_level": "AUTOCOMMIT"} if not isinstance(self.engine.dialect, RedshiftDialect_psycopg2cffi) else {}

        with self.engine.connect().execution_options(**opts) as conn:
            if isinstance(self.engine.dialect, RedshiftDialect_psycopg2cffi):
                conn.execute(sa.text("COMMIT"))
            conn.execute(sa.text('CREATE DATABASE {db_name}'.format(db_name=db_name)))

        dburl = copy.deepcopy(self.engine.url)
        try:
            dburl.database = db_name
        except AttributeError:
            dburl = dburl.set(database=db_name)

        try:
            yield db.EngineDefinition(db_connect_url=dburl, connect_args=self.engine_definition.connect_args)
        finally:
            with self.engine.connect().execution_options(**opts) as conn:
                if isinstance(self.engine.dialect, RedshiftDialect_psycopg2cffi):
                    conn.execute(sa.text("COMMIT"))
                conn.execute(sa.text('DROP DATABASE {db_name}'.format(db_name=db_name)))

    @contextlib.contextmanager
    def migrated_database(self):
        with self._database() as engine_definition:
            engine = engine_definition.engine()
            try:
                self.migrate(engine)
                yield {'definition': engine_definition, 'engine': engine}
            finally:
                engine.dispose()


def pytest_addoption(parser):
    parser.addoption("--dbdriver", action="append")


class DriverParameterizedTests:
    DEFAULT_DRIVERS = ['psycopg2', 'psycopg2cffi', 'redshift_connector']
    redshift_dialect_flavors = None

    @classmethod
    def set_drivers(cls, _drivers):
        DriverParameterizedTests.redshift_dialect_flavors = ['redshift+{}'.format(x) for x in _drivers]


def pytest_generate_tests(metafunc):
    if 'redshift_dialect_flavor' in metafunc.fixturenames:
        if DriverParameterizedTests.redshift_dialect_flavors is None:
            dbdrivers = metafunc.config.getoption("--dbdriver", default=DriverParameterizedTests.DEFAULT_DRIVERS)
            if dbdrivers is None:
                dbdrivers = DriverParameterizedTests.DEFAULT_DRIVERS
            DriverParameterizedTests.set_drivers(dbdrivers)

        metafunc.parametrize(
            'redshift_dialect_flavor',
            DriverParameterizedTests.redshift_dialect_flavors,
            ids=DriverParameterizedTests.redshift_dialect_flavors,
            scope="session")


@pytest.fixture(scope='session')
def _redshift_database_tool(connection_kwargs):
    if all([x is not None for x in connection_kwargs.values()]):
        yield DatabaseTool(engine_definition=db.redshift_engine_definition(**connection_kwargs))
    return


@pytest.fixture(scope='function')
def _redshift_engine_and_definition(_redshift_database_tool):
    with _redshift_database_tool.migrated_database() as database:
        yield database


@pytest.fixture(scope='function')
def redshift_engine(_redshift_engine_and_definition):
    return _redshift_engine_and_definition['engine']


@pytest.fixture(scope='function')
def redshift_engine_definition(_redshift_engine_and_definition):
    return _redshift_engine_and_definition['definition']


@pytest.fixture(scope='session')
def _session_scoped_redshift_engine(_redshift_database_tool):
    with _redshift_database_tool.migrated_database() as egs:
        yield egs['engine']


@pytest.fixture(scope='function')
def redshift_session(_session_scoped_redshift_engine):
    conn = _session_scoped_redshift_engine.connect()
    tx = conn.begin()

    RedshiftSession = sa.orm.sessionmaker()
    session = RedshiftSession(bind=conn)
    try:
        yield session
    finally:
        session.close()
        tx.rollback()
        conn.close()


@pytest.fixture(scope='session')
def stub_redshift_engine(redshift_dialect_flavor):
    yield make_mock_engine(redshift_dialect_flavor)


@pytest.fixture(scope='session')
def stub_redshift_dialect(stub_redshift_engine):
    yield stub_redshift_engine.dialect