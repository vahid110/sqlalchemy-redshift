import importlib
import json
import re
from collections import defaultdict, namedtuple
from logging import getLogger

import sqlalchemy as sa

# Modern resource access with fallback for Python 3.8
try:
    from importlib.resources import files
except ImportError:
    try:
        from importlib_resources import files
    except ImportError:
        # Fallback to pkg_resources for very old environments
        import pkg_resources
        files = None
from packaging.version import Version
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.dialects.postgresql.base import (PGCompiler, PGDDLCompiler,
                                                 PGDialect, PGExecutionContext,
                                                 PGIdentifierPreparer,
                                                 PGTypeCompiler)
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.dialects.postgresql.psycopg2cffi import PGDialect_psycopg2cffi
from sqlalchemy.engine import reflection
from sqlalchemy.engine.default import DefaultDialect
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import (BinaryExpression, BooleanClauseList,
                                       Delete)
from sqlalchemy.sql.type_api import TypeEngine
from sqlalchemy.types import (BIGINT, BOOLEAN, CHAR, DATE, DECIMAL, INTEGER,
                              REAL, SMALLINT, TIMESTAMP, VARCHAR, NullType)

from .commands import (AlterTableAppendCommand, Compression, CopyCommand,
                       CreateLibraryCommand, Encoding, Format,
                       RefreshMaterializedView, UnloadFromSelect)
from .ddl import (CreateMaterializedView, DropMaterializedView,
                  get_table_attributes)
from .auth import parse_auth_params, redact_credentials
from .resilience import ProductionErrorHandler, CircuitBreaker

sa_version = Version(sa.__version__)
logger = getLogger(__name__)

try:
    import alembic
except ImportError:
    pass
else:
    from alembic.ddl import postgresql
    from alembic.ddl.base import RenameTable
    compiles(RenameTable, 'redshift')(postgresql.visit_rename_table)

    if Version(alembic.__version__) >= Version('1.0.6'):
        from alembic.ddl.base import ColumnComment
        compiles(ColumnComment, 'redshift')(postgresql.visit_column_comment)

    class RedshiftImpl(postgresql.PostgresqlImpl):
        __dialect__ = 'redshift'

# "Each dialect provides the full set of typenames supported by that backend
# with its __all__ collection
# https://docs.sqlalchemy.org/en/13/core/type_basics.html#vendor-specific-types
__all__ = (
    'SMALLINT',
    'INTEGER',
    'BIGINT',
    'DECIMAL',
    'REAL',
    'BOOLEAN',
    'CHAR',
    'DATE',
    'TIMESTAMP',
    'VARCHAR',
    'DOUBLE_PRECISION',
    'GEOMETRY',
    'SUPER',
    'TIMESTAMPTZ',
    'TIMETZ',
    'HLLSKETCH',
    'ABSTIME',
    'INTERVAL',
    'JSON',
    'RedshiftArray',

    'RedshiftDialect', 'RedshiftDialect_psycopg2',
    'RedshiftDialect_psycopg2cffi', 'RedshiftDialect_redshift_connector',

    'CopyCommand', 'UnloadFromSelect', 'Compression',
    'Encoding', 'Format', 'CreateLibraryCommand', 'AlterTableAppendCommand',
    'RefreshMaterializedView',

    'CreateMaterializedView', 'DropMaterializedView'
)


# Regex for parsing and identity constraint out of adsrc, e.g.:
#   "identity"(445178, 0, '1,1'::text)
IDENTITY_RE = re.compile(r"""
    "identity" \(
      (?P<current>-?\d+)
      ,\s
      (?P<base>-?\d+)
      ,\s
      '(?P<seed>-?\d+),(?P<step>-?\d+)'
      .*
    \)
""", re.VERBOSE)

# Regex for SQL identifiers (valid table and column names)
SQL_IDENTIFIER_RE = re.compile(r"""
   [_a-zA-Z][\w$]*  # SQL standard identifier
   |                # or
   (?:"[^"]+")+     # SQL delimited (quoted) identifier
""", re.VERBOSE)

# Regex for foreign key constraints, e.g.:
#   FOREIGN KEY(col1) REFERENCES othertable (col2)
# See https://docs.aws.amazon.com/redshift/latest/dg/r_names.html
# for a definition of valid SQL identifiers.
FOREIGN_KEY_RE = re.compile(r"""
  ^FOREIGN\ KEY \s* \(   # FOREIGN KEY, arbitrary whitespace, literal '('
    (?P<columns>         # Start a group to capture the referring columns
      (?:                # Start a non-capturing group
        \s*              # Arbitrary whitespace
        ([_a-zA-Z][\w$]* | ("[^"]+")+)   # SQL identifier
        \s*              # Arbitrary whitespace
        ,?               # There will be a colon if this isn't the last one
      )+                 # Close the non-capturing group; require at least one
    )                    # Close the 'columns' group
  \s* \)                 # Arbitrary whitespace and literal ')'
  \s* REFERENCES \s*
    ((?P<referred_schema>([_a-zA-Z][\w$]* | ("[^"]*")+))\.)? # SQL identifier
    (?P<referred_table>[_a-zA-Z][\w$]* | ("[^"]*")+)         # SQL identifier
  \s* \(   # FOREIGN KEY, arbitrary whitespace, literal '('
    (?P<referred_columns> # Start a group to capture the referring columns
      (?:                # Start a non-capturing group
        \s*              # Arbitrary whitespace
        ([_a-zA-Z][\w$]* | ("[^"]+")+)   # SQL identifier
        \s*              # Arbitrary whitespace
        ,?               # There will be a colon if this isn't the last one
      )+                 # Close the non-capturing group; require at least one
    )                    # Close the 'columns' group
  \s* \)                 # Arbitrary whitespace and literal ')'
""", re.VERBOSE)

# Regex for primary key constraints, e.g.:
#   PRIMARY KEY (col1, col2)
PRIMARY_KEY_RE = re.compile(r"""
  ^PRIMARY \s* KEY \s* \(  # FOREIGN KEY, arbitrary whitespace, literal '('
    (?P<columns>         # Start a group to capture column names
      (?:
        \s*                # Arbitrary whitespace
        # SQL identifier or delimited identifier
        ( [_a-zA-Z][\w$]* | ("[^"]*")+ )
        \s*                # Arbitrary whitespace
        ,?                 # There will be a colon if this isn't the last one
      )+                  # Close the non-capturing group; require at least one
    )
  \s* \) \s*                # Arbitrary whitespace and literal ')'
""", re.VERBOSE)

# Reserved words as extracted from Redshift docs.
# See pull_reserved_words.sh at the top level of this repository
# for the code used to generate this set.
RESERVED_WORDS = set([
    "aes128", "aes256", "all", "allowoverwrite", "analyse", "analyze",
    "and", "any", "array", "as", "asc", "authorization", "az64",
    "backup", "between", "binary", "blanksasnull", "both", "bytedict",
    "bzip2", "case", "cast", "check", "collate", "column", "constraint",
    "create", "credentials", "cross", "current_date", "current_time",
    "current_timestamp", "current_user", "current_user_id", "default",
    "deferrable", "deflate", "defrag", "delta", "delta32k", "desc",
    "disable", "distinct", "do", "else", "emptyasnull", "enable",
    "encode", "encrypt", "encryption", "end", "except", "explicit",
    "false", "for", "foreign", "freeze", "from", "full", "globaldict256",
    "globaldict64k", "grant", "group", "gzip", "having", "identity",
    "ignore", "ilike", "in", "initially", "inner", "intersect", "into",
    "is", "isnull", "join", "language", "leading", "left", "like",
    "limit", "localtime", "localtimestamp", "lun", "luns", "lzo", "lzop",
    "minus", "mostly16", "mostly32", "mostly8", "natural", "new", "not",
    "notnull", "null", "nulls", "off", "offline", "offset", "oid", "old",
    "on", "only", "open", "or", "order", "outer", "overlaps", "parallel",
    "partition", "percent", "permissions", "pivot", "placing", "primary",
    "raw", "readratio", "recover", "references", "respect", "rejectlog",
    "resort", "restore", "right", "select", "session_user", "similar",
    "snapshot", "some", "sysdate", "system", "table", "tag", "tdes",
    "text255", "text32k", "then", "timestamp", "to", "top", "trailing",
    "true", "truncatecolumns", "union", "unique", "unnest", "unpivot",
    "user", "using", "verbose", "wallet", "when", "where", "with",
    "without",
])

REFLECTION_SQL = """\
    SELECT
        n.nspname as "schema",
        c.relname as "table_name",
        att.attname as "name",
        format_encoding(att.attencodingtype::integer) as "encode",
        format_type(att.atttypid, att.atttypmod) as "type",
        att.attisdistkey as "distkey",
        att.attsortkeyord as "sortkey",
        att.attnotnull as "notnull",
        pg_catalog.col_description(att.attrelid, att.attnum)
        as "comment",
        adsrc,
        attnum,
        pg_catalog.format_type(att.atttypid, att.atttypmod),
        pg_catalog.pg_get_expr(ad.adbin, ad.adrelid) AS DEFAULT,
        n.oid as "schema_oid",
        c.oid as "table_oid"
    FROM pg_catalog.pg_class c
    LEFT JOIN pg_catalog.pg_namespace n
        ON n.oid = c.relnamespace
    JOIN pg_catalog.pg_attribute att
        ON att.attrelid = c.oid
    LEFT JOIN pg_catalog.pg_attrdef ad
        ON (att.attrelid, att.attnum) = (ad.adrelid, ad.adnum)
    WHERE n.nspname !~ '^pg_'
        AND att.attnum > 0
        AND NOT att.attisdropped
        {schema_clause} {table_clause}
    UNION
    SELECT
        view_schema as "schema",
        view_name as "table_name",
        col_name as "name",
        null as "encode",
        col_type as "type",
        null as "distkey",
        0 as "sortkey",
        null as "notnull",
        null as "comment",
        null as "adsrc",
        null as "attnum",
        col_type as "format_type",
        null as "default",
        null as "schema_oid",
        null as "table_oid"
    FROM pg_get_late_binding_view_cols() cols(
        view_schema name,
        view_name name,
        col_name name,
        col_type varchar,
        col_num int)
    WHERE 1 {schema_clause} {table_clause}
    UNION
    SELECT c.schemaname AS "schema",
        c.tablename AS "table_name",
        c.columnname AS "name",
        null AS "encode",
        -- Spectrum represents data types differently.
        -- Standardize, so we can infer types.
        CASE
            WHEN c.external_type = 'int' THEN 'integer'
            WHEN c.external_type = 'float' THEN 'real'
            WHEN c.external_type = 'double' THEN 'double precision'
            WHEN c.external_type = 'timestamp'
            THEN 'timestamp without time zone'
            WHEN c.external_type ilike 'varchar%'
            THEN replace(c.external_type, 'varchar', 'character varying')
            WHEN c.external_type ilike 'decimal%'
            THEN replace(c.external_type, 'decimal', 'numeric')
            ELSE
            replace(
            replace(
                replace(c.external_type, 'decimal', 'numeric'),
                'char', 'character'),
            'varchar', 'character varying')
            END
            AS "type",
        false AS "distkey",
        0 AS "sortkey",
        null AS "notnull",
        null as "comment",
        null AS "adsrc",
        c.columnnum AS "attnum",
        CASE
            WHEN c.external_type = 'int' THEN 'integer'
            WHEN c.external_type = 'float' THEN 'real'
            WHEN c.external_type = 'double' THEN 'double precision'
            WHEN c.external_type = 'timestamp'
            THEN 'timestamp without time zone'
            WHEN c.external_type ilike 'varchar%'
            THEN replace(c.external_type, 'varchar', 'character varying')
            WHEN c.external_type ilike 'decimal%'
            THEN replace(c.external_type, 'decimal', 'numeric')
            ELSE
            replace(
            replace(
                replace(c.external_type, 'decimal', 'numeric'),
                'char', 'character'),
            'varchar', 'character varying')
            END
            AS "format_type",
        null AS "default",
        s.esoid AS "schema_oid",
        null AS "table_oid"
    FROM svv_external_columns c
    JOIN svv_external_schemas s ON s.schemaname = c.schemaname
    WHERE 1 {schema_clause} {table_clause}
    ORDER BY "schema", "table_name", "attnum";
    """


class RedshiftTypeEngine(TypeEngine):

    def _default_dialect(self, default=None):
        """
        Returns the default dialect used for TypeEngine compilation yielding
        String result.

        :meth:`~sqlalchemy.sql.type_api.TypeEngine.compile`
        """
        return RedshiftDialectMixin()


class TIMESTAMPTZ(RedshiftTypeEngine, sa.dialects.postgresql.TIMESTAMP):
    """
    Redshift defines a TIMTESTAMPTZ column type as an alias
    of TIMESTAMP WITH TIME ZONE.
    https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html

    Adding an explicit type to the RedshiftDialect allows us follow the
    SqlAlchemy conventions for "vendor-specific types."

    https://docs.sqlalchemy.org/en/13/core/type_basics.html#vendor-specific-types
    """

    __visit_name__ = 'TIMESTAMPTZ'

    def __init__(self, timezone=True, precision=None):
        # timezone param must be present as it's provided in base class so the
        # object can be instantiated with kwargs. see
        # :meth:`~sqlalchemy.dialects.postgresql.base.PGDialect._get_column_info`
        super(TIMESTAMPTZ, self).__init__(timezone=True, precision=precision)


class TIMETZ(RedshiftTypeEngine, sa.dialects.postgresql.TIME):
    """
    Redshift defines a TIMTETZ column type as an alias
    of TIME WITH TIME ZONE.
    https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html

    Adding an explicit type to the RedshiftDialect allows us follow the
    SqlAlchemy conventions for "vendor-specific types."

    https://docs.sqlalchemy.org/en/13/core/type_basics.html#vendor-specific-types
    """

    __visit_name__ = 'TIMETZ'

    def __init__(self, timezone=True, precision=None):
        # timezone param must be present as it's provided in base class so the
        # object can be instantiated with kwargs. see
        # :meth:`~sqlalchemy.dialects.postgresql.base.PGDialect._get_column_info`
        super(TIMETZ, self).__init__(timezone=True, precision=precision)


class GEOMETRY(RedshiftTypeEngine, sa.dialects.postgresql.TEXT):
    """
    Redshift defines a GEOMETRY column type
    https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html

    Adding an explicit type to the RedshiftDialect allows us follow the
    SqlAlchemy conventions for "vendor-specific types."

    https://docs.sqlalchemy.org/en/13/core/type_basics.html#vendor-specific-types
    """
    __visit_name__ = 'GEOMETRY'

    def __init__(self):
        super(GEOMETRY, self).__init__()

    def get_dbapi_type(self, dbapi):
        return dbapi.GEOMETRY


class SUPER(RedshiftTypeEngine, sa.dialects.postgresql.TEXT):
    """
    Redshift defines a SUPER column type
    https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html

    Adding an explicit type to the RedshiftDialect allows us follow the
    SqlAlchemy conventions for "vendor-specific types."

    https://docs.sqlalchemy.org/en/13/core/type_basics.html#vendor-specific-types
    """

    __visit_name__ = 'SUPER'

    def __init__(self):
        super(SUPER, self).__init__()
        self._cache = {}  # Cache for common JSON values

    def get_dbapi_type(self, dbapi):
        return dbapi.SUPER

    def bind_expression(self, bindvalue):
        return sa.func.json_parse(bindvalue)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        
        # Use cache for small, common values
        value_str = str(value)
        if len(value_str) < 100:
            if value_str not in self._cache:
                self._cache[value_str] = json.dumps(value)
            return self._cache[value_str]
        
        return json.dumps(value)
    
    def result_processor(self, dialect, coltype):
        """Process database values with caching and error handling"""
        def process(value):
            if value is None:
                return None
            if not isinstance(value, str):
                return value
            
            try:
                # Use cache for small JSON strings
                if len(value) < 100:
                    if value not in self._cache:
                        self._cache[value] = json.loads(value)
                    return self._cache[value]
                return json.loads(value)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse SUPER value as JSON: {e}")
                return value  # Return as string if JSON parsing fails
        
        return process


class HLLSKETCH(RedshiftTypeEngine, sa.dialects.postgresql.TEXT):
    """
    Redshift defines a HLLSKETCH column type
    https://docs.aws.amazon.com/redshift/latest/dg/c_Supported_data_types.html

    Adding an explicit type to the RedshiftDialect allows us follow the
    SqlAlchemy conventions for "vendor-specific types."

    https://docs.sqlalchemy.org/en/13/core/type_basics.html#vendor-specific-types
    """
    __visit_name__ = 'HLLSKETCH'

    def __init__(self):
        super(HLLSKETCH, self).__init__()

    def get_dbapi_type(self, dbapi):
        return dbapi.HLLSKETCH


class ABSTIME(RedshiftTypeEngine, sa.dialects.postgresql.TIMESTAMP):
    """
    Redshift ABSTIME data type for absolute time
    """
    __visit_name__ = 'ABSTIME'

    def __init__(self):
        super(ABSTIME, self).__init__()


class INTERVAL(RedshiftTypeEngine, sa.dialects.postgresql.INTERVAL):
    """
    Redshift INTERVAL data type
    """
    __visit_name__ = 'INTERVAL'

    def __init__(self):
        super(INTERVAL, self).__init__()


class JSON(RedshiftTypeEngine, sa.dialects.postgresql.TEXT):
    """
    JSON type that maps to SUPER in Redshift with enhanced error handling
    """
    __visit_name__ = 'JSON'
    
    def __init__(self):
        super(JSON, self).__init__()
        self._cache = {}
    
    def bind_processor(self, dialect):
        """Convert Python dict/list to JSON string with caching"""
        def process(value):
            if value is None:
                return None
            
            # Use cache for small, common values
            if isinstance(value, (dict, list)) and len(str(value)) < 100:
                cache_key = str(value)
                if cache_key not in self._cache:
                    self._cache[cache_key] = json.dumps(value)
                return self._cache[cache_key]
            
            return json.dumps(value)
        
        return process
    
    def result_processor(self, dialect, coltype):
        """Convert JSON string to Python dict/list with caching and error handling"""
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    # Use cache for small JSON strings
                    if len(value) < 100:
                        if value not in self._cache:
                            self._cache[value] = json.loads(value)
                        return self._cache[value]
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Failed to parse JSON value: {e}")
                    return value
            return value
        
        return process


class RedshiftArray(sa.types.ARRAY):
    """
    Redshift array type implementation with performance optimizations
    """
    
    def __init__(self, item_type, as_tuple=False, dimensions=None, zero_indexes=False):
        super(RedshiftArray, self).__init__(item_type, as_tuple, dimensions, zero_indexes)
    
    def bind_processor(self, dialect):
        """Process Python values for database binding with optimization"""
        item_proc = self.item_type.dialect_impl(dialect).bind_processor(dialect)
        
        def process(value):
            if value is None:
                return None
            if not isinstance(value, (list, tuple)):
                return value
            
            # Optimize for common case of no item processor
            if not item_proc:
                return list(value)
            
            # Use list comprehension for better performance
            return [item_proc(item) for item in value]
        
        return process
    
    def result_processor(self, dialect, coltype):
        """Process database values for Python use with optimization"""
        item_proc = self.item_type.dialect_impl(dialect).result_processor(dialect, coltype)
        
        def process(value):
            if value is None:
                return None
            if not isinstance(value, (list, tuple)):
                return value
            
            # Optimize for common case of no item processor
            if not item_proc:
                return list(value)
            
            # Use list comprehension for better performance
            return [item_proc(item) for item in value]
        
        return process


# Mapping for database schema inspection of Amazon Redshift datatypes
REDSHIFT_ISCHEMA_NAMES = {
    "geometry": GEOMETRY,
    "super": SUPER,
    "time with time zone": TIMETZ,
    "timestamp with time zone": TIMESTAMPTZ,
    "hllsketch": HLLSKETCH,
    "abstime": ABSTIME,
    "interval": INTERVAL,
    "intervaly2m": INTERVAL,
    "intervald2s": INTERVAL,
    "json": JSON,
}


class RelationKey(namedtuple('RelationKey', ('name', 'schema'))):
    """
    Structured tuple of table/view name and schema name.
    """
    __slots__ = ()

    def __new__(cls, name, schema=None, connection=None):
        """
        Construct a new RelationKey with an explicit schema name.
        SA 1.4/2.0 compatible version with graceful fallback.
        """
        if schema is None and connection is None:
            raise ValueError("Must specify either schema or connection")
        if schema is None:
            try:
                # Use Inspector interface for SA 2.0 compatibility
                schema = inspect(connection).default_schema_name
            except Exception:
                # Fallback for mocks or connection issues
                schema = 'public'
        return super(RelationKey, cls).__new__(cls, name, schema)

    def __str__(self):
        if self.schema is None:
            return self.name
        else:
            return self.schema + "." + self.name

    @staticmethod
    def _unquote(part):
        if (
                part is not None and part.startswith('"') and
                part.endswith('"')
        ):
            return part[1:-1]
        return part

    def unquoted(self):
        """
        Return *key* with one level of double quotes removed.

        Redshift stores some identifiers without quotes in internal tables,
        even though the name must be quoted elsewhere.
        In particular, this happens for tables named as a keyword.
        """
        return RelationKey(
            RelationKey._unquote(self.name),
            RelationKey._unquote(self.schema)
        )


class RedshiftCompiler(PGCompiler):
    def limit_clause(self, select, **kw):
        """Generate LIMIT/OFFSET clause using public SQLAlchemy API"""
        # First try parent implementation
        text = super().limit_clause(select, **kw)
        
        # If parent returns empty but we have offset, add LIMIT ALL
        if not text.strip():
            # Check for offset using both SA 1.4 and 2.0 patterns
            has_offset = (
                (hasattr(select, '_offset_clause') and select._offset_clause is not None) or
                (hasattr(select, '_offset') and select._offset is not None)
            )
            
            if has_offset:
                # Get offset value using safe attribute access
                offset_clause = (
                    getattr(select, '_offset_clause', None) or 
                    getattr(select, '_offset', None)
                )
                if offset_clause is not None:
                    text = "\n LIMIT ALL OFFSET " + self.process(offset_clause, **kw)
        
        return text

    def visit_now_func(self, fn, **kw):
        return "SYSDATE"


class RedshiftDDLCompiler(PGDDLCompiler):
    """
    Handles Redshift-specific ``CREATE TABLE`` syntax.

    Users can specify the `diststyle`, `distkey`, `sortkey` and `encode`
    properties per table and per column.

    Table level properties can be set using the dialect specific syntax. For
    example, to specify a distribution key and style you apply the following:

    >>> import sqlalchemy as sa
    >>> from sqlalchemy.schema import CreateTable
    >>> engine = sa.create_engine('redshift+psycopg2://example')
    >>> metadata = sa.MetaData()
    >>> user = sa.Table(
    ...     'user',
    ...     metadata,
    ...     sa.Column('id', sa.Integer, primary_key=True),
    ...     sa.Column('name', sa.String),
    ...     redshift_diststyle='KEY',
    ...     redshift_distkey='id',
    ...     redshift_interleaved_sortkey=['id', 'name'],
    ... )
    >>> print(CreateTable(user).compile(engine))
    <BLANKLINE>
    CREATE TABLE "user" (
        id INTEGER NOT NULL,
        name VARCHAR,
        PRIMARY KEY (id)
    ) DISTSTYLE KEY DISTKEY (id) INTERLEAVED SORTKEY (id, name)
    <BLANKLINE>
    <BLANKLINE>

    A single sort key can be applied without a wrapping list:

    >>> customer = sa.Table(
    ...     'customer',
    ...     metadata,
    ...     sa.Column('id', sa.Integer, primary_key=True),
    ...     sa.Column('name', sa.String),
    ...     redshift_sortkey='id',
    ... )
    >>> print(CreateTable(customer).compile(engine))
    <BLANKLINE>
    CREATE TABLE customer (
        id INTEGER NOT NULL,
        name VARCHAR,
        PRIMARY KEY (id)
    ) SORTKEY (id)
    <BLANKLINE>
    <BLANKLINE>

    Column-level special syntax can also be applied using Redshift dialect
    specific keyword arguments.
    For example, we can specify the ENCODE for a column:

    >>> product = sa.Table(
    ...     'product',
    ...     metadata,
    ...     sa.Column('id', sa.Integer, primary_key=True),
    ...     sa.Column('name', sa.String, redshift_encode='lzo')
    ... )
    >>> print(CreateTable(product).compile(engine))
    <BLANKLINE>
    CREATE TABLE product (
        id INTEGER NOT NULL,
        name VARCHAR ENCODE lzo,
        PRIMARY KEY (id)
    )
    <BLANKLINE>
    <BLANKLINE>

    The TIMESTAMPTZ and TIMETZ column types are also supported in the DDL.

    For SQLAlchemy versions < 1.3.0, passing Redshift dialect options
    as keyword arguments is not supported on the column level.
    Instead, a column info dictionary can be used:

    >>> product_pre_1_3_0 = sa.Table(
    ...     'product_pre_1_3_0',
    ...     metadata,
    ...     sa.Column('id', sa.Integer, primary_key=True),
    ...     sa.Column('name', sa.String, info={'encode': 'lzo'})
    ... )

    We can also specify the distkey and sortkey options:

    >>> sku = sa.Table(
    ...     'sku',
    ...     metadata,
    ...     sa.Column('id', sa.Integer, primary_key=True),
    ...     sa.Column(
    ...         'name',
    ...         sa.String,
    ...         redshift_distkey=True,
    ...         redshift_sortkey=True
    ...     )
    ... )
    >>> print(CreateTable(sku).compile(engine))
    <BLANKLINE>
    CREATE TABLE sku (
        id INTEGER NOT NULL,
        name VARCHAR DISTKEY SORTKEY,
        PRIMARY KEY (id)
    )
    <BLANKLINE>
    <BLANKLINE>
    """

    def visit_check_constraint(self, constraint, **kw):
        """
        Skip CHECK constraints - Redshift doesn't support them.
        
        Redshift silently accepts CHECK constraints but doesn't enforce them.
        To avoid errors during CREATE TABLE, we skip rendering them entirely.
        """
        return None

    def visit_create_index(self, create, include_table_schema=True, **kw):
        """
        Skip CREATE INDEX - Redshift doesn't support traditional indexes.
        
        Redshift uses sort keys and distribution keys instead of indexes.
        Returns a no-op SELECT to prevent execution errors.
        """
        # Return a no-op query that does nothing
        return "SELECT 1 WHERE FALSE"

    def visit_set_constraint_comment(self, create, **kw):
        """
        Skip COMMENT ON CONSTRAINT - Redshift doesn't support constraint comments.
        
        Since we skip CHECK constraint creation, attempting to comment on them
        causes errors. Returns a no-op SELECT to prevent execution errors.
        """
        return "SELECT 1 WHERE FALSE"

    def post_create_table(self, table):
        kwargs = ["diststyle", "distkey", "sortkey", "interleaved_sortkey"]
        info = table.dialect_options['redshift']
        info = {key: info.get(key) for key in kwargs}
        return get_table_attributes(self.preparer, **info)

    def get_column_specification(self, column, **kwargs):
        colspec = self.preparer.format_column(column)

        colspec += " " + self.dialect.type_compiler.process(column.type)

        default = self.get_column_default_string(column)
        if default is not None:
            # Identity constraints show up as *default* when reflected.
            m = IDENTITY_RE.match(default)
            if m:
                colspec += " IDENTITY({seed},{step})".format(**m.groupdict())
            else:
                colspec += " DEFAULT " + default

        colspec += self._fetch_redshift_column_attributes(column)

        if not column.nullable:
            colspec += " NOT NULL"
        return colspec

    def _fetch_redshift_column_attributes(self, column):
        text = ""
        if sa_version >= Version('1.3.0'):
            info = column.dialect_options['redshift']
        else:
            if not hasattr(column, 'info'):
                return text
            info = column.info

        identity = info.get('identity')
        if identity:
            text += " IDENTITY({0},{1})".format(identity[0], identity[1])

        encode = info.get('encode')
        if encode:
            text += " ENCODE " + encode

        distkey = info.get('distkey')
        if distkey:
            text += " DISTKEY"

        sortkey = info.get('sortkey')
        if sortkey:
            text += " SORTKEY"
        return text


class RedshiftTypeCompiler(PGTypeCompiler):

    def visit_GEOMETRY(self, type_, **kw):
        return "GEOMETRY"

    def visit_SUPER(self, type_, **kw):
        return "SUPER"

    def visit_TIMESTAMPTZ(self, type_, **kw):
        return "TIMESTAMPTZ"

    def visit_TIMETZ(self, type_, **kw):
        return "TIMETZ"

    def visit_HLLSKETCH(self, type_, **kw):
        return "HLLSKETCH"
    
    def visit_ABSTIME(self, type_, **kw):
        return "ABSTIME"
    
    def visit_INTERVAL(self, type_, **kw):
        return "INTERVAL"
    
    def visit_JSON(self, type_, **kw):
        return "SUPER"  # JSON maps to SUPER in Redshift


class RedshiftIdentifierPreparer(PGIdentifierPreparer):
    reserved_words = RESERVED_WORDS


class RedshiftDialectMixin(DefaultDialect):
    """
    Define Redshift-specific behavior.

    Most public methods are overrides of the underlying interfaces defined in
    :class:`~sqlalchemy.engine.interfaces.Dialect` and
    :class:`~sqlalchemy.engine.Inspector`.
    """

    name = 'redshift'
    max_identifier_length = 127
    
    # Redshift never supports RETURNING regardless of driver
    insert_returning = False
    use_insertmanyvalues = True  # 2.0 bulk INSERT VALUES optimization
    supports_sane_rowcount = False
    supports_indexes = False  # Redshift uses sort/dist keys, not indexes

    statement_compiler = RedshiftCompiler
    ddl_compiler = RedshiftDDLCompiler
    preparer = RedshiftIdentifierPreparer
    type_compiler = RedshiftTypeCompiler
    construct_arguments = [
        (sa.schema.Index, {
            "using": False,
            "where": None,
            "ops": {}
        }),
        (sa.schema.Table, {
            "ignore_search_path": False,
            "diststyle": None,
            "distkey": None,
            "sortkey": None,
            "interleaved_sortkey": None,
        }),
        (sa.schema.Column, {
            "encode": None,
            "distkey": None,
            "sortkey": None,
            "identity": None,
        }),
    ]

    def __init__(self, *args, **kw):
        super(RedshiftDialectMixin, self).__init__(*args, **kw)
        # Cache domains, as these will be static;
        # Redshift does not support user-created domains.
        self._domains = None

    @property
    def ischema_names(self):
        """
        Returns information about datatypes supported by Amazon Redshift.

        Used in
        :meth:`~sqlalchemy.engine.dialects.postgresql.base.PGDialect._get_column_info`.
        """
        return {
            **super(RedshiftDialectMixin, self).ischema_names,
            **REDSHIFT_ISCHEMA_NAMES
        }

    def get_multi_columns(self, connection, schema=None, filter_names=None, kind=None, scope=None, **kw):
        """
        Override SA 2.0's get_multi_columns to avoid querying pg_collation.
        
        Redshift is based on PostgreSQL 8.0.2 which predates collation support.
        SA 2.0's get_multi_columns queries pg_attribute.attcollation which doesn't exist.
        
        Properly handles kind (TABLE/VIEW/MATERIALIZED_VIEW) and scope filtering.
        """
        from sqlalchemy.engine.reflection import ObjectKind
        
        result = {}
        
        # Determine which tables/views to query based on kind and scope
        if filter_names:
            names_to_check = filter_names
        else:
            names_to_check = []
            if kind is None or kind & ObjectKind.TABLE:
                names_to_check.extend(self._get_table_names_with_scope(connection, schema, scope, **kw))
            if kind is None or kind & ObjectKind.VIEW:
                names_to_check.extend(self._get_view_names_with_scope(connection, schema, scope, **kw))
            if kind is None or kind & ObjectKind.MATERIALIZED_VIEW:
                names_to_check.extend(self._get_materialized_view_names_with_scope(connection, schema, scope, **kw))
        
        for table_name in names_to_check:
            try:
                columns = self.get_columns(connection, table_name, schema=schema, **kw)
                result[(schema, table_name)] = columns
            except Exception:
                # Skip tables that don't exist or can't be accessed
                pass
        
        return result
    
    def get_multi_pk_constraint(self, connection, schema=None, filter_names=None, kind=None, scope=None, **kw):
        """
        Override SA 2.0's get_multi_pk_constraint to avoid array_agg ORDER BY.
        
        Redshift doesn't support ORDER BY inside aggregate functions.
        Properly handles kind (TABLE/VIEW/MATERIALIZED_VIEW) and scope filtering.
        """
        from sqlalchemy.engine.reflection import ObjectKind
        
        result = {}
        
        # Get actual tables/views that exist
        actual_names = []
        if kind is None or kind & ObjectKind.TABLE:
            actual_names.extend(self._get_table_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.VIEW:
            actual_names.extend(self._get_view_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.MATERIALIZED_VIEW:
            actual_names.extend(self._get_materialized_view_names_with_scope(connection, schema, scope, **kw))
        
        # If filter_names provided, only include tables that actually exist
        if filter_names:
            names_to_check = [name for name in filter_names if name in actual_names]
        else:
            names_to_check = actual_names
        
        for table_name in names_to_check:
            try:
                pk = self.get_pk_constraint(connection, table_name, schema=schema, **kw)
                result[(schema, table_name)] = pk
            except Exception:
                pass
        
        return result
    
    def get_multi_unique_constraints(self, connection, schema=None, filter_names=None, kind=None, scope=None, **kw):
        """
        Override SA 2.0's get_multi_unique_constraints to avoid array_agg ORDER BY.
        
        Redshift doesn't support ORDER BY inside aggregate functions.
        Properly handles kind (TABLE/VIEW/MATERIALIZED_VIEW) and scope filtering.
        """
        from sqlalchemy.engine.reflection import ObjectKind
        
        result = {}
        
        # Get actual tables/views that exist
        actual_names = []
        if kind is None or kind & ObjectKind.TABLE:
            actual_names.extend(self._get_table_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.VIEW:
            actual_names.extend(self._get_view_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.MATERIALIZED_VIEW:
            actual_names.extend(self._get_materialized_view_names_with_scope(connection, schema, scope, **kw))
        
        # If filter_names provided, only include tables that actually exist
        if filter_names:
            names_to_check = [name for name in filter_names if name in actual_names]
        else:
            names_to_check = actual_names
        
        for table_name in names_to_check:
            try:
                constraints = self.get_unique_constraints(connection, table_name, schema=schema, **kw)
                result[(schema, table_name)] = constraints
            except Exception:
                pass
        
        return result
    
    def get_multi_indexes(self, connection, schema=None, filter_names=None, kind=None, scope=None, **kw):
        """
        Override SA 2.0's get_multi_indexes.
        
        Redshift doesn't support traditional indexes, always returns empty.
        Properly handles kind (TABLE/VIEW/MATERIALIZED_VIEW) and scope filtering.
        """
        from sqlalchemy.engine.reflection import ObjectKind
        
        result = {}
        
        # Get actual tables/views that exist
        actual_names = []
        if kind is None or kind & ObjectKind.TABLE:
            actual_names.extend(self._get_table_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.VIEW:
            actual_names.extend(self._get_view_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.MATERIALIZED_VIEW:
            actual_names.extend(self._get_materialized_view_names_with_scope(connection, schema, scope, **kw))
        
        # If filter_names provided, only include tables that actually exist
        if filter_names:
            names_to_check = [name for name in filter_names if name in actual_names]
        else:
            names_to_check = actual_names
        
        # Redshift doesn't support indexes, return empty list for all tables
        for table_name in names_to_check:
            result[(schema, table_name)] = []
        
        return result
    
    def get_multi_foreign_keys(self, connection, schema=None, filter_names=None, kind=None, scope=None, **kw):
        """
        Override SA 2.0's get_multi_foreign_keys to avoid array_agg ORDER BY.
        
        Redshift doesn't support ORDER BY inside aggregate functions.
        Properly handles kind (TABLE/VIEW/MATERIALIZED_VIEW) and scope filtering.
        """
        from sqlalchemy.engine.reflection import ObjectKind
        
        result = {}
        
        # Get actual tables/views that exist
        actual_names = []
        if kind is None or kind & ObjectKind.TABLE:
            actual_names.extend(self._get_table_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.VIEW:
            actual_names.extend(self._get_view_names_with_scope(connection, schema, scope, **kw))
        if kind is None or kind & ObjectKind.MATERIALIZED_VIEW:
            actual_names.extend(self._get_materialized_view_names_with_scope(connection, schema, scope, **kw))
        
        # If filter_names provided, only include tables that actually exist
        if filter_names:
            names_to_check = [name for name in filter_names if name in actual_names]
        else:
            names_to_check = actual_names
        
        for table_name in names_to_check:
            try:
                fks = self.get_foreign_keys(connection, table_name, schema=schema, **kw)
                result[(schema, table_name)] = fks
            except Exception:
                pass
        
        return result
    
    def _get_table_names_with_scope(self, connection, schema, scope, **kw):
        """Get table names filtered by ObjectScope."""
        from sqlalchemy.engine.reflection import ObjectScope
        
        if scope == ObjectScope.TEMPORARY:
            # Only temporary tables - use name-based heuristic
            return self._get_temp_table_names(connection, schema, **kw)
        elif scope == ObjectScope.DEFAULT:
            # Non-temporary tables - since Redshift doesn't expose relpersistence,
            # we can't reliably detect temp tables. Return all tables for DEFAULT.
            return self.get_table_names(connection, schema, **kw)
        else:
            # ANY or None - all tables
            return self.get_table_names(connection, schema, **kw)
    
    def _get_view_names_with_scope(self, connection, schema, scope, **kw):
        """Get view names filtered by ObjectScope."""
        from sqlalchemy.engine.reflection import ObjectScope
        
        if scope == ObjectScope.TEMPORARY:
            # Only temporary views - use name-based heuristic
            return self._get_temp_view_names(connection, schema, **kw)
        elif scope == ObjectScope.DEFAULT:
            # Non-temporary views - since Redshift doesn't expose relpersistence,
            # we can't reliably detect temp views. Return all views for DEFAULT.
            return self.get_view_names(connection, schema, **kw)
        else:
            # ANY or None - all views
            return self.get_view_names(connection, schema, **kw)
    
    def _get_materialized_view_names_with_scope(self, connection, schema, scope, **kw):
        """Get materialized view names filtered by ObjectScope."""
        from sqlalchemy.engine.reflection import ObjectScope
        
        # Redshift doesn't expose relpersistence, so we can't reliably detect temp materialized views
        # For now, return all materialized views for any scope
        return self._get_materialized_view_names(connection, schema, **kw)
    
    def _get_materialized_view_names(self, connection, schema, **kw):
        """Get materialized view names using relkind='m'."""
        return self._get_table_or_view_names('m', connection, schema, **kw)
    
    def _get_temp_table_names(self, connection, schema, **kw):
        """Get temporary table names using relpersistence."""
        return self._get_table_or_view_names('r', connection, schema, temp_only=True, **kw)
    
    def _get_temp_view_names(self, connection, schema, **kw):
        """Get temporary view names using relpersistence."""
        return self._get_table_or_view_names('v', connection, schema, temp_only=True, **kw)

    @reflection.cache
    def get_columns(self, connection, table_name, schema=None, **kw):
        """
        Return information about columns in `table_name`.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_columns`.
        """
        cols = self._get_redshift_columns(connection, table_name, schema, **kw)
        # Redshift doesn't support user-created domains, return empty dict
        if not self._domains:
            self._domains = {}
        domains = self._domains
        columns = []
        for col in cols:
            column_info = self._get_column_info(
                name=col.name, format_type=col.format_type,
                default=col.default, notnull=col.notnull, domains=domains,
                enums=[], schema=col.schema, encode=col.encode,
                comment=col.comment)
            columns.append(column_info)
        return columns
    


    @reflection.cache
    def has_table(self, connection, table_name, schema=None, **kw):
        """Check if table exists using modern Inspector-compatible approach
        
        Disables server-side cursors to avoid Redshift's limitation of one cursor per connection.
        """
        if not schema:
            try:
                # Use Inspector interface for SA 2.0 compatibility
                schema = inspect(connection).default_schema_name
            except Exception:
                # Fallback for mocks or connection issues
                schema = 'public'

        # Pass stream_results=False to avoid server-side cursor conflicts
        kw['_has_table_check'] = True
        table = self._get_all_relation_info(connection,
                                            schema=schema,
                                            table_name=table_name,
                                            **kw)

        return bool(table)

    @reflection.cache
    def get_check_constraints(self, connection, table_name, schema=None, **kw):
        table_oid = self.get_table_oid(
            connection, table_name, schema, info_cache=kw.get("info_cache")
        )
        table_oid = 'NULL' if not table_oid else table_oid

        result = connection.execute(sa.text("""
                        SELECT
                            cons.conname as name,
                            pg_get_constraintdef(cons.oid) as src
                        FROM
                            pg_catalog.pg_constraint cons
                        WHERE
                            cons.conrelid = {} AND
                            cons.contype = 'c'
                        """.format(table_oid)))
        ret = []
        for name, src in result:
            # samples:
            # "CHECK (((a > 1) AND (a < 5)))"
            # "CHECK (((a = 1) OR ((a > 2) AND (a < 5))))"
            # "CHECK (((a > 1) AND (a < 5))) NOT VALID"
            # "CHECK (some_boolean_function(a))"
            # "CHECK (((a\n < 1)\n OR\n (a\n >= 5))\n)"

            m = re.match(
                r"^CHECK *\((.+)\)( NOT VALID)?$", src, flags=re.DOTALL
            )
            if not m:
                logger.warning(f"Could not parse CHECK constraint text: {src}")
                sqltext = ""
            else:
                sqltext = re.compile(
                    r"^[\s\n]*\((.+)\)[\s\n]*$", flags=re.DOTALL
                ).sub(r"\1", m.group(1))
            entry = {"name": name, "sqltext": sqltext}
            if m and m.group(2):
                entry["dialect_options"] = {"not_valid": True}

            ret.append(entry)
        return ret

    @reflection.cache
    def get_table_oid(self, connection, table_name, schema=None, **kw):
        """Fetch the oid for schema.table_name.
        Return null if not found (external table does not have table oid)"""
        schema_field = '"{schema}".'.format(schema=schema) if schema else ""

        result = connection.execute(
            sa.text(
                """
                select '{schema_field}"{table_name}"'::regclass::oid;
                """.format(
                    schema_field=schema_field,
                    table_name=table_name
                )
            )
        )

        return result.scalar()

    @reflection.cache
    def get_pk_constraint(self, connection, table_name, schema=None, **kw):
        """
        Return information about the primary key constraint on `table_name`.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_pk_constraint`.
        """
        constraints = self._get_redshift_constraints(connection, table_name,
                                                     schema, **kw)
        pk_constraints = [c for c in constraints if c.contype == 'p']
        if not pk_constraints:
            return {'constrained_columns': [], 'name': ''}
        pk_constraint = pk_constraints[0]
        m = PRIMARY_KEY_RE.match(pk_constraint.condef)
        colstring = m.group('columns')
        constrained_columns = SQL_IDENTIFIER_RE.findall(colstring)
        return {
            'constrained_columns': constrained_columns,
            'name': pk_constraint.conname,
        }

    @reflection.cache
    def get_foreign_keys(self, connection, table_name, schema=None, **kw):
        """
        Return information about foreign keys in `table_name`.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_pk_constraint`.
        """
        constraints = self._get_redshift_constraints(connection, table_name,
                                                     schema, **kw)
        fk_constraints = [c for c in constraints if c.contype == 'f']
        uniques = defaultdict(lambda: defaultdict(dict))
        for con in fk_constraints:
            uniques[con.conname]["key"] = con.conkey
            uniques[con.conname]["condef"] = con.condef
        fkeys = []
        for conname, attrs in uniques.items():
            m = FOREIGN_KEY_RE.match(attrs['condef'])
            colstring = m.group('referred_columns')
            referred_columns = SQL_IDENTIFIER_RE.findall(colstring)
            referred_table = m.group('referred_table')
            referred_schema = m.group('referred_schema')
            colstring = m.group('columns')
            constrained_columns = SQL_IDENTIFIER_RE.findall(colstring)
            fkey_d = {
                'name': conname,
                'constrained_columns': constrained_columns,
                'referred_schema': referred_schema,
                'referred_table': referred_table,
                'referred_columns': referred_columns,
            }
            fkeys.append(fkey_d)
        return fkeys

    @reflection.cache
    def get_table_names(self, connection, schema=None, **kw):
        """
        Return a list of table names for `schema`.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_table_names`.
        """
        return self._get_table_or_view_names('r', connection, schema, **kw)

    @reflection.cache
    def get_view_names(self, connection, schema=None, **kw):
        """
        Return a list of view names for `schema`.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_view_names`.
        """
        return self._get_table_or_view_names('v', connection, schema, **kw)

    @reflection.cache
    def get_view_definition(self, connection, view_name, schema=None, **kw):
        """Return view definition.
        Given a :class:`.Connection`, a string `view_name`,
        and an optional string `schema`, return the view definition.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_view_definition`.
        """
        view = self._get_redshift_relation(connection, view_name, schema, **kw)
        return sa.text(view.view_definition)

    def get_indexes(self, connection, table_name, schema, **kw):
        """
        Return information about indexes in `table_name`.

        Because Redshift does not support traditional indexes,
        this always returns an empty list.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_indexes`.
        """
        return []

    @reflection.cache
    def get_unique_constraints(self, connection, table_name,
                               schema=None, **kw):
        """
        Return information about unique constraints in `table_name`.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.get_unique_constraints`.
        """
        constraints = self._get_redshift_constraints(connection,
                                                     table_name, schema, **kw)
        constraints = [c for c in constraints if c.contype == 'u']
        uniques = defaultdict(lambda: defaultdict(dict))
        for con in constraints:
            uniques[con.conname]["key"] = con.conkey
            uniques[con.conname]["cols"][con.attnum] = con.attname

        return [
            {'name': name,
             'column_names': [uc["cols"][i] for i in uc["key"]]}
            for name, uc in uniques.items()
        ]

    @reflection.cache
    def get_table_options(self, connection, table_name, schema, **kw):
        """
        Return a dictionary of options specified when the table of the
        given name was created.

        Overrides interface
        :meth:`~sqlalchemy.engine.Inspector.get_table_options`.
        """
        def keyfunc(column):
            num = int(column.sortkey)
            # If sortkey is interleaved, column numbers alternate
            # negative values, so take abs.
            return abs(num)
        table = self._get_redshift_relation(connection, table_name,
                                            schema, **kw)
        columns = self._get_redshift_columns(connection, table_name,
                                             schema, **kw)
        sortkey_cols = sorted([col for col in columns if col.sortkey],
                              key=keyfunc)
        interleaved = any([int(col.sortkey) < 0 for col in sortkey_cols])
        sortkey = tuple(col.name for col in sortkey_cols)
        interleaved_sortkey = None
        if interleaved:
            interleaved_sortkey = sortkey
            sortkey = None
        distkeys = [col.name for col in columns if col.distkey]
        distkey = distkeys[0] if distkeys else None
        return {
            'redshift_diststyle': table.diststyle,
            'redshift_distkey': distkey,
            'redshift_sortkey': sortkey,
            'redshift_interleaved_sortkey': interleaved_sortkey,
        }

    def _get_table_or_view_names(self, relkind, connection, schema=None, temp_only=False, **kw):
        """Get table or view names with SA 1.4/2.0 compatible schema handling"""
        if not schema:
            try:
                default_schema = inspect(connection).default_schema_name
                schema = default_schema
            except Exception:
                schema = 'public'
        info_cache = kw.get('info_cache')
        all_relations = self._get_all_relation_info(connection,
                                                    schema=schema,
                                                    info_cache=info_cache)
        relation_names = []
        for key, relation in all_relations.items():
            if key.schema == schema and relation.relkind == relkind:
                # Filter by temp_only if specified
                if temp_only:
                    # Check if temporary (relpersistence would be 't' for temp tables)
                    # Since we don't have relpersistence in our query, check table name prefix
                    # Redshift temp tables typically start with '#' or are in pg_temp schema
                    if relation.relname.startswith('#') or 'temp' in relation.relname.lower():
                        relation_names.append(key.name)
                else:
                    relation_names.append(key.name)
        return relation_names

    def _get_column_info(self, *args, **kwargs):
        kw = kwargs.copy()
        encode = kw.pop('encode', None)
        
        if sa_version >= Version('2.0.0'):
            # SQLAlchemy 2.0 removed _get_column_info, build column info directly
            name = kwargs['name']
            format_type = kwargs['format_type']
            default = kwargs.get('default')
            notnull = kwargs.get('notnull', False)
            comment = kwargs.get('comment')
            
            # Parse format_type to extract type name and parameters
            # e.g., "character varying(30)" -> ("character varying", "30")
            m = re.match(r'^\(?([^(]+?)(?:\(([^)]+)\))?\)?$', format_type)
            if m:
                coltype = m.group(1).strip()
                args_str = m.group(2)
            else:
                coltype = format_type
                args_str = None
            
            # Look up type class in ischema_names (includes Redshift types)
            type_cls = self.ischema_names.get(coltype)
            if type_cls:
                # Instantiate type with parameters if present
                if args_str:
                    # Handle common cases: length, precision/scale
                    args_parts = [p.strip() for p in args_str.split(',')]
                    try:
                        if len(args_parts) == 1:
                            type_obj = type_cls(int(args_parts[0]))
                        elif len(args_parts) == 2:
                            type_obj = type_cls(int(args_parts[0]), int(args_parts[1]))
                        else:
                            type_obj = type_cls()
                    except (ValueError, TypeError):
                        type_obj = type_cls()
                else:
                    type_obj = type_cls()
            else:
                # Unknown type, use NullType
                type_obj = NullType()
            
            # Build column_info dict matching SQLAlchemy's reflection interface
            column_info = {
                'name': name,
                'type': type_obj,
                'nullable': not notnull,
                'default': default,
            }
            if comment:
                column_info['comment'] = comment
        else:
            # SQLAlchemy 1.4: use parent's _get_column_info
            if sa_version >= Version('1.3.16'):
                # SQLAlchemy 1.3.16 introduced generated columns,
                # not supported in redshift
                kw['generated'] = ''

            if sa_version < Version('1.4.0') and 'identity' in kw:
                del kw['identity']
            elif sa_version >= Version('1.4.0') and 'identity' not in kw:
                kw['identity'] = None

            column_info = super(RedshiftDialectMixin, self)._get_column_info(
                *args,
                **kw
            )
        
        # Common post-processing for both SA 1.4 and 2.0
        if isinstance(column_info['type'], VARCHAR):
            if column_info['type'].length is None:
                column_info['type'] = NullType()
        if 'info' not in column_info:
            column_info['info'] = {}
        if encode and encode != 'none':
            column_info['info']['encode'] = encode
        return column_info

    def _get_redshift_relation(self, connection, table_name,
                               schema=None, **kw):
        info_cache = kw.get('info_cache')
        all_relations = self._get_all_relation_info(connection,
                                                    schema=schema,
                                                    table_name=table_name,
                                                    info_cache=info_cache)
        key = RelationKey(table_name, schema, connection)
        if key not in all_relations.keys():
            key = key.unquoted()
        try:
            return all_relations[key]
        except KeyError:
            raise sa.exc.NoSuchTableError(key)

    def _get_redshift_columns(self, connection, table_name, schema=None, **kw):
        info_cache = kw.get('info_cache')
        all_schema_columns = self._get_schema_column_info(
            connection,
            schema=schema,
            table_name=table_name,
            info_cache=info_cache
        )
        key = RelationKey(table_name, schema, connection)
        if key not in all_schema_columns.keys():
            key = key.unquoted()
        return all_schema_columns[key]

    def _get_redshift_constraints(self, connection, table_name,
                                  schema=None, **kw):
        info_cache = kw.get('info_cache')
        all_constraints = self._get_all_constraint_info(connection,
                                                        schema=schema,
                                                        table_name=table_name,
                                                        info_cache=info_cache)
        key = RelationKey(table_name, schema, connection)
        if key not in all_constraints.keys():
            key = key.unquoted()
        return all_constraints[key]

    @reflection.cache
    def _get_all_relation_info(self, connection, **kw):
        schema = kw.get('schema', None)
        schema_clause = (
            "AND schema = '{schema}'".format(schema=schema) if schema else ""
        )

        table_name = kw.get('table_name', None)
        table_clause = (
            "AND relname = '{table}'".format(
                table=table_name
            ) if table_name else ""
        )

        query = sa.text("""
        SELECT
          c.relkind,
          n.oid as "schema_oid",
          n.nspname as "schema",
          c.oid as "rel_oid",
          c.relname,
          CASE c.reldiststyle
            WHEN 0 THEN 'EVEN' WHEN 1 THEN 'KEY' WHEN 8 THEN 'ALL' END
            AS "diststyle",
          c.relowner AS "owner_id",
          u.usename AS "owner_name",
          TRIM(TRAILING ';' FROM pg_catalog.pg_get_viewdef(c.oid, true))
            AS "view_definition",
          pg_catalog.array_to_string(c.relacl, '\n') AS "privileges"
        FROM pg_catalog.pg_class c
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             JOIN pg_catalog.pg_user u ON u.usesysid = c.relowner
        WHERE c.relkind IN ('r', 'v', 'm', 'S', 'f')
          AND n.nspname !~ '^pg_' {schema_clause} {table_clause}
        UNION
        SELECT
            'r' AS "relkind",
            s.esoid AS "schema_oid",
            s.schemaname AS "schema",
            null AS "rel_oid",
            t.tablename AS "relname",
            null AS "diststyle",
            s.esowner AS "owner_id",
            u.usename AS "owner_name",
            null AS "view_definition",
            null AS "privileges"
        FROM
            svv_external_tables t
            JOIN svv_external_schemas s ON s.schemaname = t.schemaname
            JOIN pg_catalog.pg_user u ON u.usesysid = s.esowner
        where 1 {schema_clause} {table_clause}
        ORDER BY "relkind", "schema_oid", "schema";
        """.format(schema_clause=schema_clause, table_clause=table_clause))
        
        # Disable server-side cursor when called from has_table to avoid Redshift limitation
        if kw.get('_has_table_check'):
            result = connection.execute(query.execution_options(stream_results=False))
        else:
            result = connection.execute(query)
            
        relations = {}
        for rel in result:
            # When schema=None is passed, use None for the key instead of rel.schema
            # This ensures the key matches what callers expect
            key_schema = schema if schema is not None else None
            key = RelationKey(rel.relname, key_schema, connection)
            relations[key] = rel
        return relations

    # We fetch column info an entire schema at a time to improve performance
    # when reflecting schema for multiple tables at once.
    @reflection.cache
    def _get_schema_column_info(self, connection, **kw):
        schema = kw.get('schema', None)
        schema_clause = (
            "AND schema = '{schema}'".format(schema=schema) if schema else ""
        )

        table_name = kw.get('table_name', None)
        table_clause = (
            "AND table_name = '{table}'".format(
                table=table_name
            ) if table_name else ""
        )

        all_columns = defaultdict(list)
        result = connection.execute(sa.text(REFLECTION_SQL.format(
            schema_clause=schema_clause,
            table_clause=table_clause
        )))

        for col in result:
            # When schema=None is passed, use None for the key instead of col.schema
            # This ensures the key matches what callers expect
            key_schema = schema if schema is not None else None
            key = RelationKey(col.table_name, key_schema, connection)
            all_columns[key].append(col)

        return dict(all_columns)

    @reflection.cache
    def _get_all_constraint_info(self, connection, **kw):
        schema = kw.get('schema', None)
        schema_clause = (
            "AND schema = '{schema}'".format(schema=schema) if schema else ""
        )

        table_name = kw.get('table_name', None)
        table_clause = (
            "AND table_name = '{table}'".format(
                table=table_name
            ) if table_name else ""
        )

        result = connection.execute(sa.text("""
        SELECT
          n.nspname as "schema",
          c.relname as "table_name",
          t.contype,
          t.conname,
          t.conkey,
          a.attnum,
          a.attname,
          pg_catalog.pg_get_constraintdef(t.oid, true)::varchar(512) as condef,
          n.oid as "schema_oid",
          c.oid as "rel_oid"
        FROM pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n
          ON n.oid = c.relnamespace
        JOIN pg_catalog.pg_constraint t
          ON t.conrelid = c.oid
        JOIN pg_catalog.pg_attribute a
          ON t.conrelid = a.attrelid AND a.attnum = ANY(t.conkey)
        WHERE n.nspname !~ '^pg_' {schema_clause} {table_clause}
        UNION
        SELECT
            s.schemaname AS "schema",
            c.tablename AS "table_name",
            'p' as "contype",
            c.tablename || '_pkey' as "conname",
            array[1::SMALLINT] as "conkey",
            1 as "attnum",
            c.columnname as "attname",
            'PRIMARY KEY (' || c.columnname  || ')'::VARCHAR(512) as "condef",
            s.esoid AS "schema_oid",
            null AS "rel_oid"
        FROM
            svv_external_columns c
            JOIN svv_external_schemas s ON s.schemaname = c.schemaname
        where 1 {schema_clause} {table_clause}
        ORDER BY "schema", "table_name"
        """.format(schema_clause=schema_clause, table_clause=table_clause)))
        all_constraints = defaultdict(list)
        for con in result:
            # When schema=None is passed, use None for the key instead of con.schema
            # This ensures the key matches what callers expect
            key_schema = schema if schema is not None else None
            key = RelationKey(con.table_name, key_schema, connection)
            all_constraints[key].append(con)
        return all_constraints

    def _set_backslash_escapes(self, connection):
        self._backslash_escapes = False


class Psycopg2RedshiftDialectMixin(RedshiftDialectMixin):
    """
    Define behavior specific to ``psycopg2``.

    Most public methods are overrides of the underlying interfaces defined in
    :class:`~sqlalchemy.engine.interfaces.Dialect` and
    :class:`~sqlalchemy.engine.Inspector`.
    """
    def create_connect_args(self, *args, **kwargs):
        """
        Build DB-API compatible connection arguments.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.create_connect_args`.
        """
        # Get CA bundle path using modern importlib.resources
        if files is not None:
            try:
                ca_bundle_path = str(files('sqlalchemy_redshift').joinpath('redshift-ca-bundle.crt'))
            except Exception:
                # Fallback for development/editable installs
                import os
                ca_bundle_path = os.path.join(os.path.dirname(__file__), 'redshift-ca-bundle.crt')
        else:
            # pkg_resources fallback
            ca_bundle_path = pkg_resources.resource_filename(__name__, 'redshift-ca-bundle.crt')
        
        default_args = {
            'sslmode': 'verify-full',
            'sslrootcert': ca_bundle_path,
        }
        cargs, cparams = (
            super(Psycopg2RedshiftDialectMixin, self).create_connect_args(
                *args, **kwargs
            )
        )
        default_args.update(cparams)
        return cargs, default_args

    def set_isolation_level(self, connection, level):
        """
        Sets the isolation level for the current transaction.
        Redshift only supports READ COMMITTED and AUTOCOMMIT.
        """
        level = level.replace("_", " ")
        
        # adjust for ConnectionFairy possibly being present
        if hasattr(connection, "connection"):
            connection = connection.connection
        
        if level == "AUTOCOMMIT":
            connection.autocommit = True
        elif level.upper() in ("READ COMMITTED", "READ_COMMITTED"):
            connection.autocommit = False
            # Redshift default is READ committed, no explicit SET needed
        else:
            raise sa.exc.ArgumentError(
                f"Redshift only supports READ committed and autocommit isolation levels, got: {level}"
            )
    
    def reset_isolation_level(self, dbapi_connection):
        """Reset isolation level to default (READ COMMITTED)"""
        # adjust for ConnectionFairy possibly being present
        if hasattr(dbapi_connection, "connection"):
            dbapi_connection = dbapi_connection.connection
        
        # Reset to default read committed (autocommit=False)
        dbapi_connection.autocommit = False

    @classmethod
    def import_dbapi(cls):
        try:
            return importlib.import_module(cls.driver)
        except ImportError:
            raise ImportError(
                'No module named {}'.format(cls.driver)
            )
    
    @classmethod
    def dbapi(cls):
        """Backwards compatibility - use import_dbapi instead"""
        return cls.import_dbapi()


class RedshiftDialect_psycopg2(
    Psycopg2RedshiftDialectMixin, PGDialect_psycopg2
):
    supports_statement_cache = False
    
    @classmethod
    def import_dbapi(cls):
        """Modern import method for SQLAlchemy 2.0 compatibility"""
        try:
            return importlib.import_module(cls.driver)
        except ImportError:
            raise ImportError(
                'No module named {}'.format(cls.driver)
            )


# Add RedshiftDialect synonym for backwards compatibility.
RedshiftDialect = RedshiftDialect_psycopg2


class RedshiftDialect_psycopg2cffi(
    Psycopg2RedshiftDialectMixin, PGDialect_psycopg2cffi
):
    supports_statement_cache = False
    
    @classmethod
    def import_dbapi(cls):
        """Modern import method for SQLAlchemy 2.0 compatibility"""
        try:
            return importlib.import_module(cls.driver)
        except ImportError:
            raise ImportError(
                'No module named {}'.format(cls.driver)
            )


class RedshiftDialect_redshift_connector(RedshiftDialectMixin, PGDialect):
    # SQLAlchemy 2.0 compatibility flags - critical for Redshift
    supports_statement_cache = True      # Enable for performance

    class RedshiftCompiler_redshift_connector(RedshiftCompiler, PGCompiler):
        def visit_mod_binary(self, binary, operator, **kw):
            return (
                self.process(binary.left, **kw)
                + " %% "
                + self.process(binary.right, **kw)
            )

        def post_process_text(self, text):
            from sqlalchemy import util
            if "%%" in text:
                util.warn(
                    "The SQLAlchemy postgresql dialect "
                    "now automatically escapes '%' in text() "
                    "expressions to '%%'."
                )
            return text.replace("%", "%%")

    class RedshiftExecutionContext_redshift_connector(PGExecutionContext):
        def pre_exec(self):
            if not self.compiled:
                return

    driver = 'redshift_connector'

    supports_unicode_statements = True

    supports_unicode_binds = True

    default_paramstyle = "format"
    supports_sane_multi_rowcount = True
    statement_compiler = RedshiftCompiler_redshift_connector
    execution_ctx_cls = RedshiftExecutionContext_redshift_connector

    supports_statement_cache = True   # Enable for performance
    use_setinputsizes = False  # not implemented in redshift_connector

    def __init__(self, client_encoding=None, **kwargs):
        super(
            RedshiftDialect_redshift_connector, self
        ).__init__(client_encoding=client_encoding, **kwargs)
        self.client_encoding = client_encoding
        # Initialize production-grade error handling
        self.error_handler = ProductionErrorHandler()
        self.circuit_breaker = CircuitBreaker()

    @classmethod
    def import_dbapi(cls):
        try:
            driver_module = importlib.import_module(cls.driver)

            # Starting v2.0.908 driver converts description column names to str
            if Version(driver_module.__version__) < Version('2.0.908'):
                cls.description_encoding = "use_encoding"
            else:
                cls.description_encoding = None

            return driver_module
        except ImportError:
            raise ImportError(
                'No module named redshift_connector. Please install '
                'redshift_connector to use this sqlalchemy dialect.'
            )
    
    @classmethod
    def dbapi(cls):
        """Backwards compatibility - use import_dbapi instead"""
        return cls.import_dbapi()

    def set_client_encoding(self, connection, client_encoding):
        """
        Sets the client-side encoding using the provided connection object.
        """
        # adjust for ConnectionFairy possibly being present
        if hasattr(connection, "connection"):
            connection = connection.connection

        cursor = connection.cursor()
        cursor.execute("SET CLIENT_ENCODING TO '" + client_encoding + "'")
        cursor.execute("COMMIT")
        cursor.close()

    def set_isolation_level(self, connection, level):
        """
        Sets the isolation level for the current transaction.

        Additionally, autocommit can be enabled on the underlying
        db-api connection object via argument level='AUTOCOMMIT'.

        See Amazon Redshift documentation for information on supported
        isolation levels.
        https://docs.aws.amazon.com/redshift/latest/dg/r_BEGIN.html
        """
        level = level.replace("_", " ")

        # adjust for ConnectionFairy possibly being present
        if hasattr(connection, "connection"):
            connection = connection.connection

        if level == "AUTOCOMMIT":
            connection.autocommit = True
        elif level.upper() in ("READ COMMITTED", "READ_COMMITTED"):
            connection.autocommit = False
            # Redshift default is read committed, no explicit SET needed
        else:
            # Don't call super() for unsupported levels, just set to read committed
            connection.autocommit = False
    
    def _assert_and_set_isolation_level(self, dbapi_conn, level):
        """Override to handle AUTOCOMMIT for redshift_connector"""
        level = level.replace("_", " ").upper()
        
        if level == "AUTOCOMMIT":
            dbapi_conn.autocommit = True
        elif level in ("READ COMMITTED", "READ_COMMITTED"):
            dbapi_conn.autocommit = False
        else:
            # For redshift_connector, only support AUTOCOMMIT and READ COMMITTED
            dbapi_conn.autocommit = False
    
    def reset_isolation_level(self, dbapi_connection):
        """Reset isolation level to default (READ COMMITTED)"""
        # adjust for ConnectionFairy possibly being present
        if hasattr(dbapi_connection, "connection"):
            dbapi_connection = dbapi_connection.connection
        
        # Reset to default read committed (autocommit=False)
        dbapi_connection.autocommit = False

    def on_connect(self):
        fns = []

        def on_connect(conn):
            from sqlalchemy.sql.elements import quoted_name
            try:
                # SQLAlchemy 1.4 compatibility
                from sqlalchemy import util
                if hasattr(util, 'text_type'):
                    conn.py_types[quoted_name] = conn.py_types[util.text_type]
                else:
                    # SQLAlchemy 2.0 - text_type is just str
                    conn.py_types[quoted_name] = conn.py_types[str]
            except (ImportError, AttributeError):
                # Fallback - use str type
                conn.py_types[quoted_name] = conn.py_types[str]

        fns.append(on_connect)
        
        # Add Redshift-specific connection parameters
        def configure_redshift(conn):
            cursor = conn.cursor()
            try:
                # Enable query result caching
                cursor.execute("SET enable_result_cache_for_session = on")
                # Set query group for monitoring
                cursor.execute("SET query_group = 'sqlalchemy'")
                # Optimize for analytical workloads
                cursor.execute("SET statement_timeout = 0")
            except Exception as e:
                logger.warning(f"Failed to set Redshift parameters: {e}")
            finally:
                cursor.close()
        
        fns.append(configure_redshift)

        if self.client_encoding is not None:

            def on_connect(conn):
                self.set_client_encoding(conn, self.client_encoding)

            fns.append(on_connect)

        if self.isolation_level is not None:

            def on_connect(conn):
                self.set_isolation_level(conn, self.isolation_level)

            fns.append(on_connect)

        if len(fns) > 0:

            def on_connect(conn):
                for fn in fns:
                    fn(conn)

            return on_connect
        else:
            return None

    def create_connect_args(self, *args, **kwargs):
        """
        Build DB-API compatible connection arguments with enhanced authentication.

        Overrides interface
        :meth:`~sqlalchemy.engine.interfaces.Dialect.create_connect_args`.
        """
        default_args = {
            'sslmode': 'verify-full',
            'ssl': True,
            'application_name': 'sqlalchemy-redshift'
        }
        cargs, cparams = super(RedshiftDialectMixin, self).create_connect_args(
            *args, **kwargs
        )
        
        # Enhanced authentication parameter parsing
        if args and hasattr(args[0], 'query'):
            auth_params = parse_auth_params(args[0])
            cparams.update(auth_params)
            
            # Log connection attempt with redacted credentials
            safe_url = redact_credentials(str(args[0]))
            logger.info(f"Connecting to Redshift: {safe_url}")
        
        # set client_encoding so it is picked up by on_connect(), as
        # redshift_connector does not have client_encoding connection parameter
        self.client_encoding = cparams.pop(
            'client_encoding', self.client_encoding
        )

        if 'port' in cparams:
            cparams['port'] = int(cparams['port'])

        if 'username' in cparams:
            cparams['user'] = cparams['username']
            del cparams['username']

        default_args.update(cparams)
        return cargs, default_args
    
    def is_disconnect(self, e, connection, cursor):
        """Enhanced disconnect detection using error handler"""
        return self.error_handler.is_disconnect_error(e)
    
    def do_rollback(self, dbapi_connection):
        """Handle rollback with proper error handling and cache clearing"""
        try:
            dbapi_connection.rollback()
        except Exception as e:
            # Clear prepared statement cache on rollback errors
            if hasattr(dbapi_connection, '_caches'):
                try:
                    dbapi_connection._caches.clear()
                except:
                    pass
            if not self.is_disconnect(e, dbapi_connection, None):
                raise
    
    def do_commit(self, dbapi_connection):
        """Handle commit with proper error handling"""
        try:
            dbapi_connection.commit()
        except Exception as e:
            if not self.is_disconnect(e, dbapi_connection, None):
                raise
    
    def do_ping(self, dbapi_connection):
        """Connection health check for pool management"""
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Exception:
            return False
    
    def get_pool_class(self, url):
        """Return optimized pool class for Redshift"""
        from sqlalchemy.pool import QueuePool
        return QueuePool
    
    def get_default_pool_size(self):
        """Return default pool size optimized for Redshift"""
        return 5
    
    def get_default_max_overflow(self):
        """Return default max overflow optimized for Redshift"""
        return 10


def gen_columns_from_children(root):
    """
    Generates columns that are being used in child elements of the delete query
    this will be used to determine tables for the using clause.
    :param root: the delete query
    :return: a generator of columns
    """
    if isinstance(root, (Delete, BinaryExpression, BooleanClauseList)):
        for child in root.get_children():
            yc = gen_columns_from_children(child)
            for it in yc:
                yield it
    elif isinstance(root, sa.Column):
        yield root


@compiles(Delete, 'redshift')
def visit_delete_stmt(element, compiler, **kwargs):
    """
    Adds redshift-dialect specific compilation rule for the
    delete statement.

    Redshift DELETE syntax can be found here:
    https://docs.aws.amazon.com/redshift/latest/dg/r_DELETE.html

    .. :code-block: sql

        DELETE [ FROM ] table_name
        [ { USING } table_name, ...]
        [ WHERE condition ]

    By default, SqlAlchemy compiles DELETE statements with the
    syntax:

    .. :code-block: sql

        DELETE [ FROM ] table_name
        [ WHERE condition ]

    problem illustration:

    >>> from sqlalchemy import Table, Column, Integer, MetaData, delete
    >>> from sqlalchemy_redshift.dialect import RedshiftDialect_psycopg2
    >>> meta = MetaData()
    >>> table1 = Table(
    ... 'table_1',
    ... meta,
    ... Column('pk', Integer, primary_key=True)
    ... )
    ...
    >>> table2 = Table(
    ... 'table_2',
    ... meta,
    ... Column('pk', Integer, primary_key=True)
    ... )
    ...
    >>> del_stmt = delete(table1).where(table1.c.pk==table2.c.pk)
    >>> str(del_stmt.compile(dialect=RedshiftDialect_psycopg2()))
    'DELETE FROM table_1 USING table_2 WHERE table_1.pk = table_2.pk'
    >>> str(del_stmt)
    'DELETE FROM table_1 , table_2 WHERE table_1.pk = table_2.pk'
    >>> del_stmt2 = delete(table1)
    >>> str(del_stmt2)
    'DELETE FROM table_1'
    >>> del_stmt3 = delete(table1).where(table1.c.pk > 1000)
    >>> str(del_stmt3)
    'DELETE FROM table_1 WHERE table_1.pk > :pk_1'
    >>> str(del_stmt3.compile(dialect=RedshiftDialect_psycopg2()))
    'DELETE FROM table_1 WHERE table_1.pk >  %(pk_1)s'
    """

    # Set empty strings for the default where clause and using clause
    whereclause = ''
    usingclause = ''

    # determine if the delete query needs a ``USING`` injected
    # by inspecting the whereclause's children & their children...
    # first, the where clause text is buit, if applicable
    # then, the using clause text is built, if applicable
    # note:
    #   the tables in the using clause are sorted in the order in
    #   which they first appear in the where clause.
    delete_stmt_table = compiler.process(element.table, asfrom=True, **kwargs)

    if sa_version >= Version('1.4.0'):
        if element.whereclause is not None:
            clause = compiler.process(element.whereclause, **kwargs)
            if clause:
                whereclause = ' WHERE {clause}'.format(clause=clause)
    else:
        whereclause_tuple = element.get_children()
        if whereclause_tuple:
            whereclause = ' WHERE {clause}'.format(
                clause=compiler.process(*whereclause_tuple, **kwargs)
            )

    if whereclause:
        usingclause_tables = []
        whereclause_columns = gen_columns_from_children(element)
        for col in whereclause_columns:
            table = compiler.process(col.table, asfrom=True, **kwargs)
            if table != delete_stmt_table and \
                    table not in usingclause_tables:
                usingclause_tables.append(table)
        if usingclause_tables:
            usingclause = ' USING {clause}'.format(
                clause=', '.join(usingclause_tables)
            )

    return 'DELETE FROM {table}{using}{where}'.format(
        table=delete_stmt_table,
        using=usingclause,
        where=whereclause)
