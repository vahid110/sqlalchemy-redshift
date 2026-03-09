"""
Redshift-specific test requirements and exclusions for SQLAlchemy test suite.

Documents which SQLAlchemy features are not supported by Redshift.
"""

from sqlalchemy.testing import exclusions
from sqlalchemy.testing.requirements import SuiteRequirements


class Requirements(SuiteRequirements):
    """Redshift-specific test requirements"""
    
    @property
    def returning(self):
        """Redshift doesn't support RETURNING clause.
        
        Note: SQLAlchemy respects the insert_returning/update_returning/delete_returning
        flags and strips RETURNING clauses before compilation, so statements with
        .returning() never reach the database. The ReturningGuardsTest expects a
        DBAPIError from the database, but SQLAlchemy prevents the invalid SQL from
        being sent, so these tests cannot pass as written.
        """
        return exclusions.closed()
    
    @property
    def for_update(self):
        """Redshift doesn't support FOR UPDATE clause"""
        return exclusions.closed()
    
    @property
    def indexes(self):
        """Redshift doesn't support traditional indexes"""
        return exclusions.closed()
    
    @property
    def index_reflection(self):
        """Redshift doesn't support index reflection (no indexes exist)"""
        return exclusions.closed()
    
    @property
    def check_constraints(self):
        """CHECK constraints are informational only, not enforced"""
        return exclusions.closed()
    
    @property
    def check_constraint_reflection(self):
        """CHECK constraints not supported in CREATE TABLE"""
        return exclusions.closed()
    
    @property
    def foreign_key_constraint_reflection(self):
        """Foreign keys are metadata-only, not enforced"""
        return exclusions.open()
    
    @property
    def savepoints(self):
        """Redshift doesn't support savepoints"""
        return exclusions.closed()
    
    @property
    def two_phase_transactions(self):
        """Redshift doesn't support two-phase commit"""
        return exclusions.closed()
    
    @property
    def sequences(self):
        """Redshift uses IDENTITY instead of sequences"""
        return exclusions.closed()
    
    @property
    def temporary_tables(self):
        """Redshift supports temporary tables"""
        return exclusions.open()
    
    @property
    def views(self):
        """Redshift supports views"""
        return exclusions.open()
    
    @property
    def schemas(self):
        """Redshift supports schemas"""
        return exclusions.open()
    
    @property
    def binary_literals(self):
        """Redshift doesn't support BYTEA type"""
        return exclusions.closed()
    
    @property
    def binary_comparisons(self):
        """Redshift doesn't support BYTEA type"""
        return exclusions.closed()
    
    @property
    def foreign_key_constraint_option_reflection_ondelete(self):
        """Redshift doesn't reflect ON DELETE options"""
        return exclusions.closed()
    
    @property
    def foreign_key_constraint_option_reflection_onupdate(self):
        """Redshift doesn't reflect ON UPDATE options"""
        return exclusions.closed()
    
    @property
    def temp_table_reflection(self):
        """Redshift has limited temp table reflection"""
        return exclusions.closed()
    
    @property
    def distinct_on(self):
        """Redshift doesn't support DISTINCT ON"""
        return exclusions.closed()
    
    @property
    def is_distinct_from(self):
        """Redshift doesn't support IS DISTINCT FROM"""
        return exclusions.closed()
    
    @property
    def supports_is_distinct_from(self):
        """Redshift doesn't support IS DISTINCT FROM operator"""
        return exclusions.closed()
    
    @property
    def uuid_data_type(self):
        """Redshift doesn't have native UUID type"""
        return exclusions.closed()
    
    @property
    def enum_data_type(self):
        """Redshift doesn't support ENUM types"""
        return exclusions.closed()
    
    @property
    def autoincrement_insert(self):
        """Redshift uses IDENTITY columns, not sequences for autoincrement"""
        return exclusions.closed()
    
    @property
    def duplicate_key_raises_integrity_error(self):
        """Redshift doesn't enforce PRIMARY KEY constraints (informational only)"""
        return exclusions.closed()
    
    @property
    def autoincrement_without_sequence(self):
        """Redshift uses IDENTITY, but test assumes sequence behavior"""
        return exclusions.closed()
    
    @property
    def reflect_table_options(self):
        """Redshift supports reflecting table options (diststyle, distkey, sortkey)"""
        return exclusions.open()
