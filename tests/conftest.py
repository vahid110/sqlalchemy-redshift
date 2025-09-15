import os
import copy
import contextlib
import itertools
import uuid
import functools
import configparser
from logging import getLogger

from rs_sqla_test_utils.db import EngineDefinition

import pytest
import sqlalchemy as sa


from rs_sqla_test_utils import db
from rs_sqla_test_utils.utils import make_mock_engine

logger = getLogger(__name__)

_unicode = type(u'')


@pytest.fixture(scope="session")
def connection_kwargs(redshift_dialect_flavor):
    """ Connection parameters for running integration tests
    against an existing Redshift instance.

    Supports both environment variables and config.ini file.
    Priority: environment variables > config.ini > skip test
    """
    # Try environment variables first
    pgpassword = os.environ.get("PGPASSWORD")
    host = os.getenv("REDSHIFT_HOST")
    port = os.getenv("REDSHIFT_PORT")
    username = os.getenv("REDSHIFT_USERNAME")
    database = os.getenv("REDSHIFT_DATABASE")
    
    # If no env vars, try config.ini
    if not all([pgpassword, host, username]):
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path)
            
            if 'database-config' in config:
                db_config = config['database-config']
                host = host or db_config.get('host')
                port = port or db_config.get('port')
                username = username or db_config.get('user')
                pgpassword = pgpassword or db_config.get('password')
                database = database or db_config.get('database')
    
    # Skip if still missing required params
    if not all([pgpassword, host, username]):
        pytest.skip("No database credentials found. Set environment variables or create config.ini")

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": pgpassword,
        "database": database or "dev",
        "dialect": redshift_dialect_flavor,
    }


@pytest.fixture(scope="session")
def iam_role_arn():
    """ The iam_role_arn fixture constructs the ARN for the IAM role. If provided,
    the following environment variable will be used.

    - REDSHIFT_IAM_ROLE_ARN
    """
    return os.getenv(
        "REDSHIFT_IAM_ROLE_ARN",
        "arn:aws:iam::000123456789:role/redshiftrole"
    )


@pytest.fixture(scope="session")
def aws_account_id(iam_role_arn):
    """ Returns the AWS account ID from the iam_role_arn. If provided,
    the following environment variable will be used.

    - REDSHIFT_IAM_ROLE_ARN
    """
    try:
        return iam_role_arn.split(":")[4]
    except IndexError:
        pytest.fail("Unable to parse iam_role_name from iam_role_arn")


@pytest.fixture(scope="session")
def iam_role_name(iam_role_arn):
    """ Returns the IAM role name from the iam_role_arn. If provided,
    the following environment variable will be used.

    - REDSHIFT_IAM_ROLE_ARN
    """
    try:
        return iam_role_arn.split("/")[1]
    except IndexError:
        pytest.fail("Unable to parse iam_role_name from iam_role_arn")


@pytest.fixture(scope="session")
def iam_role_arn_with_aws_partition():
    """ The iam_role_arn_with_aws_partition fixture allows the developer to
    pass in their own IAM_ROLE_ARN for other Redshift instances by setting
    the following environment variable:
    REDSHIFT_IAM_ROLE_ARN_WITH_AWS_PARTITION
    """
    return os.getenv(
        "REDSHIFT_IAM_ROLE_ARN_WITH_AWS_PARTITION",
        "arn:aws-us-gov:iam::000123456789:role/redshiftrole"
    )


@pytest.fixture(scope="session")
def aws_partition(iam_role_arn_with_aws_partition):
    """ Returns the AWS partition from the iam_role_arn_with_aws_partition.
    If provided, the following environment variable will be used.

    - REDSHIFT_IAM_ROLE_ARN_WITH_AWS_PARTITION
    """
    try:
        return iam_role_arn_with_aws_partition.split(":")[1]
    except IndexError:
        pytest.fail(
            "Unable to parse aws_partition from "
            "iam_role_arn_with_aws_partition"
        )


@pytest.fixture(scope="session")
def iam_role_arns():
    """
    The iam_role_arns fixture allows the developer to pass in their own
    IAM_ROLE_ARNs for other Redshift instances by setting the following
    environment variable: REDSHIFT_IAM_ROLE_ARNS

    e.g.
        REDSHIFT_IAM_ROLE_ARNS="arn:aws:iam::123:role/role,arn:aws:iam::123:role/role2"
    """
    default_arns_as_string = (
        "arn:aws:iam::000123456789:role/redshiftrole,"
        "arn:aws:iam::000123456789:role/redshiftrole2"
    )
    arns = os.getenv("REDSHIFT_IAM_ROLE_ARNS", default_arns_as_string)
    return arns.split(",")


def database_name_generator():
    template = 'testdb_{uuid}_{count}'
    db_uuid = _unicode(uuid.uuid1()).replace('-', '')
    for i in itertools.count():
        yield template.format(
            uuid=db_uuid,
            count=i,
        )


database_name = functools.partial(next, database_name_generator())


class DatabaseTool(object):
    """
    Abstracts the creation and destruction of migrated databases.
    """

    def __init__(self, engine_definition: EngineDefinition):
        self.engine_definition = engine_definition
        self.engine = engine_definition.engine()

    def migrate(self, engine):
        from rs_sqla_test_utils import models
        models.Base.metadata.create_all(bind=engine)

    @contextlib.contextmanager
    def _database(self):
        from sqlalchemy_redshift.dialect import \
            RedshiftDialect_psycopg2cffi

        db_name = database_name()
        opts = (
            {"isolation_level": "AUTOCOMMIT"}
            if not isinstance(
                self.engine.dialect, RedshiftDialect_psycopg2cffi
            )
            else {}
        )

        with self.engine.connect().execution_options(**opts) as conn:
            if isinstance(self.engine.dialect, RedshiftDialect_psycopg2cffi):
                conn.execute(sa.text("COMMIT"))
            conn.execute(
                sa.text('CREATE DATABASE {db_name}'.format(db_name=db_name))
            )

        dburl = copy.deepcopy(self.engine.url)
        try:
            dburl.database = db_name
        except AttributeError:
            dburl = dburl.set(database=db_name)

        try:
            yield db.EngineDefinition(
                db_connect_url=dburl,
                connect_args=self.engine_definition.connect_args,
            )
        finally:
            with self.engine.connect().execution_options(**opts) as conn:
                if isinstance(
                        self.engine.dialect, RedshiftDialect_psycopg2cffi
                ):
                    conn.execute(sa.text("COMMIT"))
                conn.execute(
                    sa.text('DROP DATABASE {db_name}'.format(db_name=db_name))
                )

    @contextlib.contextmanager
    def migrated_database(self):
        """
        Test fixture for testing real commits/rollbacks.

        Creates and migrates a fresh database for every test.
        """
        with self._database() as engine_definition:
            engine = engine_definition.engine()
            try:
                self.migrate(engine)
                yield {
                    'definition': engine_definition,
                    'engine': engine,
                }
            finally:
                engine.dispose()


def pytest_addoption(parser):
    """
    Pytest option to define which dbdrivers to run the test suite with.

    """
    parser.addoption("--dbdriver", action="append")


class DriverParameterizedTests:
    """
    Helper class for generating fixture params using pytest config opts.

    """
    DEFAULT_DRIVERS = ['psycopg2', 'psycopg2cffi']
    redshift_dialect_flavors = None

    @classmethod
    def set_drivers(cls,  _drivers):
        DriverParameterizedTests.redshift_dialect_flavors = [
            'redshift+{}'.format(x) for x in _drivers
        ]


def pytest_generate_tests(metafunc):

    if 'redshift_dialect_flavor' in metafunc.fixturenames:
        if DriverParameterizedTests.redshift_dialect_flavors is None:
            dbdrivers = metafunc.config.getoption(
                "--dbdriver", default=DriverParameterizedTests.DEFAULT_DRIVERS
            )
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
        yield DatabaseTool(
            engine_definition=db.redshift_engine_definition(
                **connection_kwargs
            )
        )
    return


@pytest.fixture(scope='function')
def _redshift_engine_and_definition(_redshift_database_tool):
    with _redshift_database_tool.migrated_database() as database:
        yield database


@pytest.fixture(scope='function')
def redshift_engine(_redshift_engine_and_definition):
    """
    A redshift engine for a freshly migrated database.
    """
    return _redshift_engine_and_definition['engine']


@pytest.fixture(scope='function')
def redshift_engine_definition(_redshift_engine_and_definition):
    """
    A redshift engine definition for a freshly migrated database.
    """
    return _redshift_engine_and_definition['definition']


@pytest.fixture(scope='session')
def _session_scoped_redshift_engine(_redshift_database_tool):
    """
    Private fixture to maintain a db for the entire test session.
    """
    with _redshift_database_tool.migrated_database() as egs:
        yield egs['engine']


@pytest.fixture(scope='function')
def redshift_session(_session_scoped_redshift_engine):
    """
    A redshift session that rolls back all operations.

    The engine and db is maintained for the entire test session for efficiency.
    """
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
