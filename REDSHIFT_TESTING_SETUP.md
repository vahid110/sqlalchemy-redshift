# Redshift Testing Setup

This document explains how to configure a real Redshift connection for integration tests.

## Configuration Options

You can configure Redshift connection details using either:
1. **config.ini file** (recommended for local development)
2. **Environment variables** (recommended for CI/CD)

### Option 1: config.ini File

Create a `config.ini` file in the repository root:

```ini
[database-config]
host=your-cluster.region.redshift.amazonaws.com
port=5439
database=dev
user=testuser
password=your_password

[iam-config]
# Optional: For IAM authentication testing
iam_role_arn=arn:aws:iam::123456789012:role/RedshiftRole
aws_access_key_id=AKIAIOSFODNN7EXAMPLE
aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region=us-east-1
```

**Note**: `config.ini` is already in `.gitignore` to prevent accidental commits.

### Option 2: Environment Variables

Set the following environment variables to enable integration tests with a real Redshift cluster:

### Required Variables
```bash
export PGPASSWORD="your_redshift_password"
export REDSHIFT_HOST="your-cluster.region.redshift.amazonaws.com"
export REDSHIFT_PORT="5439"
export REDSHIFT_USERNAME="your_username"
export REDSHIFT_DATABASE="your_database"
```

### Optional Variables for IAM Role Testing
```bash
export REDSHIFT_IAM_ROLE_ARN="arn:aws:iam::123456789012:role/RedshiftRole"
export REDSHIFT_IAM_ROLE_ARN_WITH_AWS_PARTITION="arn:aws-us-gov:iam::123456789012:role/RedshiftRole"
export REDSHIFT_IAM_ROLE_ARNS="arn:aws:iam::123456789012:role/Role1,arn:aws:iam::123456789012:role/Role2"
```

## Example Configuration

### For Standard Username/Password Authentication:
```bash
export PGPASSWORD="MySecurePassword123"
export REDSHIFT_HOST="my-redshift-cluster.abc123.us-east-1.redshift.amazonaws.com"
export REDSHIFT_PORT="5439"
export REDSHIFT_USERNAME="testuser"
export REDSHIFT_DATABASE="dev"
```

### For IAM Authentication:
```bash
export PGPASSWORD=""  # Can be empty for IAM auth
export REDSHIFT_HOST="my-redshift-cluster.abc123.us-east-1.redshift.amazonaws.com"
export REDSHIFT_USERNAME="iamuser"
export REDSHIFT_DATABASE="dev"
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"
```

## Running Integration Tests

Once environment variables are set, run the integration tests:

### Using pytest directly:
```bash
# Run all tests (including integration tests)
python -m pytest tests/ -v

# Run only integration tests that require real connection
python -m pytest tests/ -v -k "reflection_inspection"

# Run specific integration test files
python -m pytest tests/test_dialect_types.py -v
```

### Using tox (recommended):
```bash
# Run tests with tox (automatically handles environment variables)
tox -e py310-pg28-sa14

# Run with specific Python/SQLAlchemy versions
tox -e py39-pg28-sa13   # Python 3.9, SQLAlchemy 1.3
tox -e py310-pg28-sa14  # Python 3.10, SQLAlchemy 1.4
```

**Note**: The `tox.ini` file is already configured to pass through the required environment variables (`PGPASSWORD`, `REDSHIFT_HOST`, etc.)

## Test Database Requirements

The integration tests will:
1. Create temporary databases for testing
2. Create and drop test tables
3. Test reflection and metadata operations
4. Clean up after themselves

### Required Permissions
Your Redshift user needs:
- `CREATE` permission on the database
- `DROP` permission on created objects
- `SELECT` permission for reflection tests
- `INSERT/UPDATE/DELETE` for data operation tests

### Recommended Test Setup
1. Use a dedicated test cluster or database
2. Use a test user with limited permissions
3. Ensure the cluster allows connections from your IP
4. Consider using Redshift Serverless for cost-effective testing

## Security Notes

- **config.ini is in .gitignore** - never commit credentials to version control
- Use IAM roles when possible instead of access keys
- Consider using AWS Secrets Manager for credential management
- Rotate credentials regularly
- Use least-privilege access for test users
- **Priority**: Environment variables override config.ini settings

## Troubleshooting

### Common Issues:
1. **Connection timeout**: Check security groups and network ACLs
2. **Authentication failed**: Verify credentials and user permissions
3. **Database not found**: Ensure the database exists and user has access
4. **SSL errors**: Redshift requires SSL by default

### Debug Connection:
```bash
# Test connection manually
psql -h $REDSHIFT_HOST -p $REDSHIFT_PORT -U $REDSHIFT_USERNAME -d $REDSHIFT_DATABASE

# Enable debug logging in tests
export SQLALCHEMY_WARN_20=1
python -m pytest tests/ -v -s --log-cli-level=DEBUG
```

## Cost Optimization

To minimize costs during testing:
1. Use Redshift Serverless for development testing
2. Pause clusters when not in use
3. Use smaller node types for testing
4. Set up automated cluster shutdown
5. Monitor usage with AWS Cost Explorer