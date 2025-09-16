try:
    from importlib.metadata import version, PackageNotFoundError  # Py3.8+
except ImportError:  # pragma: no cover
    from importlib_metadata import version, PackageNotFoundError  # backport

# Check psycopg2 version if available
for package in ['psycopg2', 'psycopg2-binary', 'psycopg2cffi']:
    try:
        pkg_version = version(package)
        from packaging.version import parse
        if parse(pkg_version) < parse('2.5'):
            raise ImportError('Minimum required version for psycopg2 is 2.5')
        break
    except PackageNotFoundError:
        pass

try:
    __version__ = version("sqlalchemy-redshift")
except PackageNotFoundError:
    __version__ = "0+local"

from sqlalchemy.dialects import registry  # noqa

registry.register(
    "redshift", "sqlalchemy_redshift.dialect",
    "RedshiftDialect_psycopg2"
)
registry.register(
    "redshift.psycopg2", "sqlalchemy_redshift.dialect",
    "RedshiftDialect_psycopg2"
)
registry.register(
    'redshift+psycopg2cffi', 'sqlalchemy_redshift.dialect',
    'RedshiftDialect_psycopg2cffi',
)

registry.register(
    "redshift+redshift_connector", "sqlalchemy_redshift.dialect",
    "RedshiftDialect_redshift_connector"
)
