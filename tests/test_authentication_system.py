"""
Tests for the enhanced authentication system
"""
import pytest
from unittest.mock import Mock

from sqlalchemy_redshift.auth import parse_auth_params, redact_credentials
from sqlalchemy_redshift.auth import (
    create_profile_engine, create_serverless_engine, 
    create_saml_engine, create_azure_engine, create_jwt_engine
)
from sqlalchemy_redshift.dialect import RedshiftDialect_redshift_connector


class TestAuthenticationParsing:
    """Test authentication parameter parsing"""
    
    def test_parse_auth_params_basic(self):
        """Test basic authentication parameter parsing"""
        # Mock URL object
        mock_url = Mock()
        mock_url.username = 'testuser'
        mock_url.password = 'testpass'
        mock_url.host = 'test.redshift.amazonaws.com'
        mock_url.port = 5439
        mock_url.database = 'testdb'
        mock_url.query = {}
        
        auth_params = parse_auth_params(mock_url)
        
        assert auth_params['user'] == 'testuser'
        assert auth_params['password'] == 'testpass'
        assert auth_params['host'] == 'test.redshift.amazonaws.com'
        assert auth_params['port'] == 5439
        assert auth_params['database'] == 'testdb'

    def test_parse_auth_params_iam(self):
        """Test IAM authentication parameter parsing"""
        # Mock URL object
        mock_url = Mock()
        mock_url.username = 'testuser'
        mock_url.password = None
        mock_url.host = 'test.redshift.amazonaws.com'
        mock_url.port = None
        mock_url.database = 'testdb'
        mock_url.query = {
            'iam': 'true',
            'access_key_id': 'AKIATEST',
            'secret_access_key': 'testsecret',
            'region': 'us-east-1'
        }
        
        auth_params = parse_auth_params(mock_url)
        
        assert auth_params['iam'] is True
        assert auth_params['access_key_id'] == 'AKIATEST'
        assert auth_params['secret_access_key'] == 'testsecret'
        assert auth_params['region'] == 'us-east-1'

    def test_credential_redaction(self):
        """Test credential redaction functionality"""
        connection_string = "redshift+redshift_connector://user@host/db?password=secret123&secret_access_key=verysecret&session_token=jwt_token_here"
        
        redacted = redact_credentials(connection_string)
        
        assert 'secret123' not in redacted
        assert 'verysecret' not in redacted
        assert 'jwt_token_here' not in redacted
        assert '***' in redacted


class TestAuthenticationHelpers:
    """Test authentication helper functions"""
    
    def test_authentication_helper_functions(self):
        """Test that authentication helper functions work"""
        # These should not raise exceptions
        try:
            # Test profile engine creation
            engine = create_profile_engine(
                host='test.redshift.amazonaws.com',
                database='testdb',
                profile='test-profile',
                cluster_identifier='test-cluster'
            )
            assert engine is not None
            
            # Test serverless engine creation
            engine = create_serverless_engine(
                workgroup='test-workgroup',
                database='testdb',
                account_id='123456789012',
                region='us-east-1'
            )
            assert engine is not None
            
        except Exception as e:
            pytest.fail(f"Authentication helper functions failed: {e}")


class TestDialectAuthenticationIntegration:
    """Test dialect integration with authentication system"""
    
    def test_dialect_authentication_integration(self):
        """Test that dialect integrates with authentication system"""
        redshift_dialect = RedshiftDialect_redshift_connector()
        
        # Verify authentication components are present
        assert hasattr(redshift_dialect, 'error_handler')
        
        # Verify enhanced connection methods
        assert hasattr(redshift_dialect, 'do_ping')
        assert hasattr(redshift_dialect, 'is_disconnect')

    def test_create_connect_args_method(self):
        """Test create_connect_args method exists and works"""
        dialect_instance = RedshiftDialect_redshift_connector()
        
        # Mock URL object with proper translate_connect_args method
        mock_url = Mock()
        mock_url.host = 'test.redshift.amazonaws.com'
        mock_url.port = 5439
        mock_url.database = 'testdb'
        mock_url.username = 'testuser'
        mock_url.password = 'testpass'
        mock_url.query = {}
        mock_url.translate_connect_args.return_value = {
            'host': 'test.redshift.amazonaws.com',
            'port': 5439,
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        
        # Should not raise an exception
        try:
            args, kwargs = dialect_instance.create_connect_args(mock_url)
            assert isinstance(args, (list, tuple))
            assert isinstance(kwargs, dict)
        except Exception as e:
            pytest.fail(f"create_connect_args failed: {e}")