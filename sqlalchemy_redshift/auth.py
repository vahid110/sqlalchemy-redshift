"""
Enhanced Authentication Support for Redshift SQLAlchemy Dialect
Supports all 9 authentication methods with secure credential handling
"""

import re
from logging import getLogger
from sqlalchemy import create_engine

logger = getLogger(__name__)

# Credential redaction patterns for secure logging
CREDENTIAL_PATTERNS = [
    (re.compile(r'(password=)[^&\s]+'), r'\1***'),
    (re.compile(r'(secret_access_key=)[^&\s]+'), r'\1***'),
    (re.compile(r'(session_token=)[^&\s]+'), r'\1***'),
    (re.compile(r'(client_secret=)[^&\s]+'), r'\1***'),
    (re.compile(r'(web_identity_token=)[^&\s]+'), r'\1***'),
]

def redact_credentials(connection_string):
    """Redact sensitive information from connection strings for logging"""
    redacted = connection_string
    for pattern, replacement in CREDENTIAL_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted

def parse_auth_params(url):
    """Parse authentication parameters from SQLAlchemy URL"""
    opts = {}
    
    # Basic connection parameters
    if url.username:
        opts['user'] = url.username
    if url.password:
        opts['password'] = url.password
    if url.host:
        opts['host'] = url.host
    if url.port:
        opts['port'] = url.port
    if url.database:
        opts['database'] = url.database
        
    # Process query parameters for authentication
    query_params = dict(url.query)
    
    # IAM Authentication
    if query_params.get('iam') == 'true':
        opts['iam'] = True
        
        # AWS Credentials
        for key in ['access_key_id', 'secret_access_key', 'session_token', 'profile']:
            if key in query_params:
                opts[key] = query_params[key]
        
        # Cluster/Serverless parameters
        for key in ['cluster_identifier', 'serverless_work_group', 'serverless_acct_id', 'region']:
            if key in query_params:
                opts[key] = query_params[key]
        
        # IdP Authentication
        if 'credentials_provider' in query_params:
            opts['credentials_provider'] = query_params['credentials_provider']
            # IdP-specific parameters
            for key in ['idp_host', 'client_id', 'client_secret', 'tenant', 'web_identity_token', 'role_arn']:
                if key in query_params:
                    opts[key] = query_params[key]
        
        # Advanced IAM options
        for key in ['group_federation', 'auto_create', 'iam_disable_cache', 'duration']:
            if key in query_params:
                if key in ['group_federation', 'auto_create', 'iam_disable_cache']:
                    opts[key] = query_params[key] == 'true'
                else:
                    opts[key] = int(query_params[key])
    
    # SSL/Security parameters
    for key in ['ssl', 'sslmode']:
        if key in query_params:
            opts[key] = query_params[key]
    
    # Add any remaining query parameters
    for key, value in query_params.items():
        if key not in opts:
            opts[key] = value
    
    return opts

# Authentication helper functions for common patterns

def create_profile_engine(host, database, profile='default', cluster_identifier=None, **kwargs):
    """Create engine with AWS profile authentication"""
    url_params = f"iam=true&profile={profile}"
    if cluster_identifier:
        url_params += f"&cluster_identifier={cluster_identifier}"
    
    url = f"redshift+redshift_connector://dummy:dummy@{host}/{database}?{url_params}"
    return create_engine(url, **kwargs)

def create_serverless_engine(workgroup, database, account_id, region='us-east-1', 
                           access_key_id=None, secret_access_key=None, **kwargs):
    """Create engine for Redshift Serverless authentication"""
    url_params = f"iam=true&serverless_work_group={workgroup}&serverless_acct_id={account_id}&region={region}"
    
    if access_key_id and secret_access_key:
        url_params += f"&access_key_id={access_key_id}&secret_access_key={secret_access_key}"
    
    url = f"redshift+redshift_connector://dummy:dummy@dummy/{database}?{url_params}"
    return create_engine(url, **kwargs)

def create_saml_engine(host, database, provider, idp_host, user, password, 
                      cluster_identifier=None, **kwargs):
    """Create engine with SAML authentication"""
    url_params = f"iam=true&credentials_provider={provider}&idp_host={idp_host}"
    if cluster_identifier:
        url_params += f"&cluster_identifier={cluster_identifier}"
    
    url = f"redshift+redshift_connector://{user}:{password}@{host}/{database}?{url_params}"
    return create_engine(url, **kwargs)

def create_azure_engine(host, database, client_id, tenant, client_secret, 
                       cluster_identifier=None, **kwargs):
    """Create engine with Azure AD authentication"""
    url_params = f"iam=true&credentials_provider=AzureCredentialsProvider&client_id={client_id}&tenant={tenant}&client_secret={client_secret}"
    if cluster_identifier:
        url_params += f"&cluster_identifier={cluster_identifier}"
    
    url = f"redshift+redshift_connector://dummy:dummy@{host}/{database}?{url_params}"
    return create_engine(url, **kwargs)

def create_jwt_engine(host, database, web_identity_token, role_arn, 
                     cluster_identifier=None, **kwargs):
    """Create engine with JWT token authentication"""
    url_params = f"iam=true&credentials_provider=JwtCredentialsProvider&web_identity_token={web_identity_token}&role_arn={role_arn}"
    if cluster_identifier:
        url_params += f"&cluster_identifier={cluster_identifier}"
    
    url = f"redshift+redshift_connector://dummy:dummy@{host}/{database}?{url_params}"
    return create_engine(url, **kwargs)