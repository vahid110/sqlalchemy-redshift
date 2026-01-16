__author__ = 'haleemur'

import re

import sqlalchemy as sa
from packaging.version import Version
from sqlalchemy.engine import url as sa_url


sa_version = Version(sa.__version__)
is_sqlalchemy_2 = sa_version >= Version('2.0.0')


def clean(query):
    query = re.sub(r'\s+ENCODE\s+\w+', '', query)
    query = re.sub(r'\s+CONSTRAINT\s+[a-zA-Z0-9_".]+', '', query)
    return re.sub(r'\s+', ' ', query).strip()


def compile_query(q, _dialect):
    return str(q.compile(
        dialect=_dialect,
        compile_kwargs={'literal_binds': True})
    )


def get_url_builder():
    if sa_version < Version('1.4.0'):
        return sa_url.URL

    # Changed in version 1.4: The URL object is now an immutable object.
    # To create a URL, use make_url() or URL.create()
    return sa_url.URL.create


def make_mock_engine(name):
    """
    Creates a mock sqlalchemy engine for testing dialect functionality

    """
    url_builder = get_url_builder()
    if Version(sa.__version__) >= Version('1.4.0'):
        return sa.create_mock_engine(url_builder(
            drivername=name
        ), executor=None)
    else:
        return sa.create_engine(url_builder(
            drivername=name,
        ), strategy='mock', executor=None)


def create_metadata_with_bind(bind):
    """
    Creates MetaData with bind in a version-compatible way.
    
    SA 1.4: MetaData(bind=engine) is deprecated but works
    SA 2.0: MetaData(bind=engine) removed, use metadata.reflect(bind=engine)
    
    Returns MetaData instance ready for use.
    """
    from sqlalchemy import MetaData
    
    if sa_version >= Version('2.0.0'):
        # SA 2.0: Create metadata without bind, caller must use reflect(bind=...)
        return MetaData()
    else:
        # SA 1.4: Use bind parameter (deprecated but functional)
        return MetaData(bind=bind)
