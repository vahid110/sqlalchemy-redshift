"""
Real cluster smoke tests - only run when environment variables are present.

These tests require actual Redshift cluster credentials and are intended for:
- Maintainer validation with real clusters
- CI environments with secrets configured
- Local development with proper credentials

Set these environment variables to enable:
- REDSHIFT_TEST_HOST
- REDSHIFT_TEST_DATABASE  
- REDSHIFT_TEST_USER
- REDSHIFT_TEST_PASSWORD (or use IAM)
- REDSHIFT_TEST_S3_BUCKET (for COPY/UNLOAD tests)
"""

import os
import pytest
import sqlalchemy as sa
from sqlalchemy import text, create_engine
from sqlalchemy.pool import NullPool
try:
    from .conftest import TEST_CONFIG
except ImportError:
    # Fallback for direct execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from conftest import TEST_CONFIG


# Tests will fail with clear error messages if credentials are missing


@pytest.fixture(scope="module", params=['psycopg2', 'redshift_connector'])
def real_engine(request):
    """Create engine for real Redshift cluster testing"""
    driver = request.param
    
    # Let redshift_connector fail with clear error if not available
    if driver == 'redshift_connector':
        try:
            import redshift_connector
        except ImportError:
            raise ImportError(f"redshift_connector not available for {driver} tests")
    
    host = TEST_CONFIG.get('REDSHIFT_TEST_HOST')
    database = TEST_CONFIG.get('REDSHIFT_TEST_DATABASE')
    user = TEST_CONFIG.get('REDSHIFT_TEST_USER')
    password = TEST_CONFIG.get('REDSHIFT_TEST_PASSWORD')
    port = TEST_CONFIG.get('REDSHIFT_TEST_PORT', '5439')
    
    # Build connection URL
    if password:
        url = f"redshift+{driver}://{user}:{password}@{host}:{port}/{database}"
    else:
        # Assume IAM authentication
        url = f"redshift+{driver}://{user}@{host}:{port}/{database}?iam=true"
    
    engine = create_engine(
        url,
        poolclass=NullPool,  # Don't pool connections for tests
        echo=False
    )
    
    yield engine
    engine.dispose()


class TestRealClusterSmoke:
    """Smoke tests against real Redshift cluster"""
    
    def test_basic_select_one(self, real_engine):
        """Basic connectivity test - SELECT 1"""
        with real_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test_col"))
            row = result.fetchone()
            assert row[0] == 1
    
    def test_basic_select_sysdate(self, real_engine):
        """Test Redshift-specific function compilation"""
        with real_engine.connect() as conn:
            result = conn.execute(text("SELECT SYSDATE"))
            row = result.fetchone()
            assert row[0] is not None  # Should return current timestamp
    
    def test_create_temp_table_and_insert(self, real_engine):
        """Test DDL and DML operations"""
        with real_engine.connect() as conn:
            # Create temporary table
            conn.execute(text("""
                CREATE TEMP TABLE test_smoke_table (
                    id INTEGER,
                    name VARCHAR(50),
                    created_at TIMESTAMP DEFAULT SYSDATE
                )
            """))
            
            # Insert data
            conn.execute(text("""
                INSERT INTO test_smoke_table (id, name) 
                VALUES (1, 'test'), (2, 'smoke')
            """))
            
            # Query data
            result = conn.execute(text("""
                SELECT id, name FROM test_smoke_table ORDER BY id
            """))
            rows = result.fetchall()
            
            assert len(rows) == 2
            assert rows[0][0] == 1
            assert rows[0][1] == 'test'
            assert rows[1][0] == 2
            assert rows[1][1] == 'smoke'
            
            conn.commit()
    
    def test_super_json_type(self, real_engine):
        """Test SUPER/JSON type handling"""
        with real_engine.connect() as conn:
            # Create temp table with SUPER column
            conn.execute(text("""
                CREATE TEMP TABLE test_super_table (
                    id INTEGER,
                    data SUPER
                )
            """))
            
            # Insert JSON data
            conn.execute(text("""
                INSERT INTO test_super_table (id, data) 
                VALUES (1, JSON_PARSE('{"key": "value", "number": 42}'))
            """))
            
            # Query JSON data
            result = conn.execute(text("""
                SELECT id, data FROM test_super_table
            """))
            row = result.fetchone()
            
            assert row[0] == 1
            # Data should be returned as string or parsed JSON
            assert row[1] is not None
            
            conn.commit()


class TestRealClusterCopyUnload:
    """COPY/UNLOAD tests requiring S3 access"""
    
    def test_copy_unload_autocommit_isolation(self, real_engine):
        """Test COPY/UNLOAD with AUTOCOMMIT isolation level"""
        s3_bucket = TEST_CONFIG.get('REDSHIFT_TEST_S3_BUCKET')
        iam_role = TEST_CONFIG.get('REDSHIFT_TEST_IAM_ROLE')
        s3_prefix = f"s3://{s3_bucket}/sqlalchemy-test/"
        
        # Create engine with AUTOCOMMIT isolation
        autocommit_engine = real_engine.execution_options(
            isolation_level="AUTOCOMMIT"
        )
        
        with autocommit_engine.connect() as conn:
            # Create temp table for testing
            conn.execute(text("""
                CREATE TEMP TABLE test_copy_table (
                    id INTEGER,
                    name VARCHAR(50)
                )
            """))
            
            # Insert test data
            conn.execute(text("""
                INSERT INTO test_copy_table VALUES 
                (1, 'test1'), (2, 'test2'), (3, 'test3')
            """))
            
            # UNLOAD data to S3 (requires AUTOCOMMIT)
            unload_sql = f"""
                UNLOAD ('SELECT id, name FROM test_copy_table ORDER BY id')
                TO '{s3_prefix}test_unload_'
                IAM_ROLE '{iam_role}'
                FORMAT AS CSV
                HEADER
                ALLOWOVERWRITE
            """
            
            try:
                result = conn.execute(text(unload_sql))
                # UNLOAD should succeed with AUTOCOMMIT
                assert result is not None
                
                # Clean up - delete the S3 files if possible
                # (This would require additional S3 permissions)
                
            except Exception as e:
                # Let all errors fail the test with clear messages
                raise Exception(f"UNLOAD test failed: {e}")
    
    def test_copy_from_s3_format(self, real_engine):
        """Test COPY command from S3.
        
        Requires: S3 file at {bucket}/test-data/sample.csv with content:
            id,name
            1,test1
            2,test2
            3,test3
        """
        s3_bucket = TEST_CONFIG.get('REDSHIFT_TEST_S3_BUCKET')
        iam_role = TEST_CONFIG.get('REDSHIFT_TEST_IAM_ROLE')
        s3_path = f"s3://{s3_bucket}/test-data/sample.csv"
        
        # Create engine with AUTOCOMMIT isolation
        autocommit_engine = real_engine.execution_options(
            isolation_level="AUTOCOMMIT"
        )
        
        with autocommit_engine.connect() as conn:
            # Create temp table for COPY target
            conn.execute(text("""
                CREATE TEMP TABLE test_copy_target (
                    id INTEGER,
                    name VARCHAR(50)
                )
            """))
            
            # Test COPY command format (will likely fail due to missing file)
            copy_sql = f"""
                COPY test_copy_target (id, name)
                FROM '{s3_path}'
                IAM_ROLE '{iam_role}'
                FORMAT AS CSV
                IGNOREHEADER 1
            """
            
            try:
                conn.execute(text(copy_sql))
            except Exception as e:
                # Let the test fail with the actual error for better debugging
                raise Exception(f"COPY test failed: {e}")


if __name__ == "__main__":
    # Allow running tests directly with proper environment
    pytest.main([__file__, "-v"])