"""
Test configuration and fixtures for sqlalchemy-redshift tests.

Supports loading credentials from:
1. Environment variables (REDSHIFT_TEST_*)
2. INI file (tests/redshift_test.ini)
"""

import os
import configparser
from pathlib import Path


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
                    'REDSHIFT_TEST_S3_BUCKET': section.get('s3_bucket')
                })
    
    # Set environment variables for other modules
    for key, value in config.items():
        if value:
            os.environ[key] = value
    
    return config


# Load config at import time
TEST_CONFIG = load_test_config()