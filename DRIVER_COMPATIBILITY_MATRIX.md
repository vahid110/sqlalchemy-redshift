# Driver Compatibility Matrix

## Supported Drivers

| Driver | Status | Performance | Use Case |
|--------|--------|-------------|----------|
| redshift_connector | ✅ Recommended | Best | Production, all auth methods |
| psycopg2 | ✅ Supported | Good | Legacy compatibility |
| psycopg2cffi | ✅ Supported | Good | PyPy compatibility |

## Feature Comparison

### Core Features
| Feature | redshift_connector | psycopg2 | psycopg2cffi |
|---------|-------------------|----------|--------------|
| Basic SQL operations | ✅ | ✅ | ✅ |
| Connection pooling | ✅ | ✅ | ✅ |
| SSL/TLS support | ✅ | ✅ | ✅ |
| Transaction support | ✅ | ✅ | ✅ |
| COPY/UNLOAD commands | ✅ | ✅ | ✅ |

### Performance Features
| Feature | redshift_connector | psycopg2 | psycopg2cffi |
|---------|-------------------|----------|--------------|
| Statement caching | ✅ | ❌ | ❌ |
| Connection health checks | ✅ | ✅ | ✅ |
| Optimized connection params | ✅ | ✅ | ✅ |
| Error handling | ✅ Enhanced | ✅ Basic | ✅ Basic |
| Circuit breaker | ✅ | ❌ | ❌ |

### Authentication Methods
| Method | redshift_connector | psycopg2 | psycopg2cffi |
|--------|-------------------|----------|--------------|
| Username/Password | ✅ | ✅ | ✅ |
| IAM Database Auth | ✅ | ❌ | ❌ |
| IAM Identity Center | ✅ | ❌ | ❌ |
| SAML/ADFS | ✅ | ❌ | ❌ |
| Azure AD | ✅ | ❌ | ❌ |
| Okta | ✅ | ❌ | ❌ |
| JWT | ✅ | ❌ | ❌ |
| Browser SAML | ✅ | ❌ | ❌ |
| Profile-based | ✅ | ❌ | ❌ |

## Driver-Specific Configuration

### redshift_connector (Recommended)
```python
# Full feature set with all authentication methods
engine = create_engine(
    'redshift+redshift_connector://user:pass@host:5439/db',
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

**Advantages:**
- All 9 authentication methods supported
- Best performance with statement caching
- Production-grade error handling
- Circuit breaker for resilience
- Native Redshift optimizations

**Use for:**
- New projects
- Production deployments
- Advanced authentication needs

### psycopg2 (Legacy Compatible)
```python
# Basic PostgreSQL-compatible driver
engine = create_engine(
    'redshift+psycopg2://user:pass@host:5439/db',
    pool_size=5,
    max_overflow=10
)
```

**Advantages:**
- Mature, stable driver
- Wide compatibility
- Good performance

**Limitations:**
- Only username/password auth
- No statement caching
- Basic error handling

**Use for:**
- Legacy applications
- Simple authentication needs
- PostgreSQL tool compatibility

### psycopg2cffi (PyPy Compatible)
```python
# PyPy-compatible driver
engine = create_engine(
    'redshift+psycopg2cffi://user:pass@host:5439/db',
    pool_size=5,
    max_overflow=10
)
```

**Advantages:**
- PyPy compatibility
- Similar to psycopg2 API
- Good performance on PyPy

**Limitations:**
- Only username/password auth
- No statement caching
- Basic error handling

**Use for:**
- PyPy deployments
- Performance-critical PyPy applications

## Test Results

### Driver Loading Test
```
redshift_connector   ✅ Driver: redshift_connector, Cache: True, DBAPI: redshift_connector
psycopg2             ✅ Driver: psycopg2, Cache: False, DBAPI: psycopg2  
psycopg2cffi         ✅ Driver: psycopg2cffi, Cache: False, DBAPI: psycopg2cffi
```

### Compatibility Test Results
| Test | redshift_connector | psycopg2 | psycopg2cffi |
|------|-------------------|----------|--------------|
| Dialect instantiation | ✅ | ✅ | ✅ |
| DBAPI loading | ✅ | ✅ | ✅ |
| SQL compilation | ✅ | ✅ | ✅ |
| Type system | ✅ | ✅ | ✅ |
| DDL extensions | ✅ | ✅ | ✅ |

## Installation

### redshift_connector
```bash
pip install redshift_connector
# or
pip install amazon-redshift-python-driver
```

### psycopg2
```bash
pip install psycopg2-binary
# or for source build
pip install psycopg2
```

### psycopg2cffi
```bash
pip install psycopg2cffi
```

## Migration Guide

### From psycopg2 to redshift_connector
```python
# Old
engine = create_engine('redshift+psycopg2://user:pass@host:5439/db')

# New - just change the driver part
engine = create_engine('redshift+redshift_connector://user:pass@host:5439/db')
```

**Benefits of migration:**
- 🚀 Better performance with statement caching
- 🔐 Access to all 9 authentication methods
- 🛡️ Enhanced error handling and resilience
- 📊 Better monitoring and observability

### From psycopg2cffi to redshift_connector
Same as above - just change the driver in the connection string.

## Recommendations

### For New Projects
- **Use redshift_connector** - best performance and features
- Enable statement caching and connection health checks
- Use advanced authentication methods when available

### For Existing Projects
- **psycopg2/psycopg2cffi work fine** - no urgent need to migrate
- **Consider redshift_connector** for performance improvements
- Migration is simple - just change connection string

### For Production
- **redshift_connector recommended** for new deployments
- **All drivers are production-ready** and stable
- Choose based on authentication and performance needs