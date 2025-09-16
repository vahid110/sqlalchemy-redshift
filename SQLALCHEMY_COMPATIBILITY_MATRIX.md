# SQLAlchemy Compatibility Matrix

## Supported Versions

| SQLAlchemy Version | Status | Notes |
|-------------------|--------|-------|
| 1.4.x | ✅ Fully Supported | Tested with 1.4.54 |
| 2.0.x | ✅ Fully Supported | Modern syntax, performance optimizations |


## Feature Compatibility

### Core Features
| Feature | SA 1.4.x | SA 2.0.x |
|---------|----------|----------|
| Basic SQL compilation | ✅ | ✅ |
| Type system | ✅ | ✅ |
| Reflection | ✅ | ✅ |
| Connection pooling | ✅ | ✅ |
| COPY/UNLOAD commands | ✅ | ✅ |
| DDL extensions | ✅ | ✅ |

### Performance Features
| Feature | SA 1.4.x | SA 2.0.x |
|---------|----------|----------|
| Statement caching | ✅ | ✅ |
| Connection health checks | ✅ | ✅ |
| Bulk insert optimization | ⚠️ Limited | ✅ |
| Modern select syntax | ✅ | ✅ |
| Legacy select syntax | ✅ | ⚠️ Deprecated |

### Redshift-Specific Features
| Feature | SA 1.4.x | SA 2.0.x |
|---------|----------|----------|
| SUPER type | ✅ | ✅ |
| GEOMETRY type | ✅ | ✅ |
| JSON type | ✅ | ✅ |
| DISTSTYLE/DISTKEY | ✅ | ✅ |
| SORTKEY/INTERLEAVED | ✅ | ✅ |
| Materialized views | ✅ | ✅ |

## Capability Flags by Version

### SQLAlchemy 1.4.x
```python
insert_returning = False              # Redshift doesn't support RETURNING
use_insertmanyvalues = True          # Available but limited effect
supports_sane_rowcount = False       # Redshift rowcount quirks
supports_statement_cache = True      # Performance optimization
```

### SQLAlchemy 2.0.x+
```python
insert_returning = False              # Redshift doesn't support RETURNING  
use_insertmanyvalues = True          # Full bulk insert optimization
supports_sane_rowcount = False       # Redshift rowcount quirks
supports_statement_cache = True      # Enhanced caching
```

## Migration Guide

### From SQLAlchemy 1.4 to 2.0+

#### ✅ No Changes Needed
- COPY/UNLOAD commands work identically
- DDL extensions (DISTSTYLE, DISTKEY, SORTKEY) unchanged
- Type system fully compatible
- Connection strings unchanged

#### ⚠️ Syntax Updates Recommended
```python
# Old (1.4) - still works in 2.0 but deprecated
select([table.c.column])

# New (2.0+) - recommended
select(table.c.column)
```

#### 🚀 Performance Improvements in 2.0+
- Better bulk insert performance with `use_insertmanyvalues=True`
- Enhanced statement caching
- Improved connection pooling
- Modern query compilation

## Testing Matrix

### Current Test Coverage
- ✅ SQLAlchemy 1.4.54 - All tests passing
- ✅ Basic 2.0+ compatibility verified
- ✅ All Redshift-specific features working

### Recommended Testing
```bash
# Test with SQLAlchemy 1.4.x
pip install "sqlalchemy>=1.4,<2.0"
python -m pytest tests/

# Test with SQLAlchemy 2.0.x  
pip install "sqlalchemy>=2.0,<2.1"
python -m pytest tests/


```

## Known Issues

### SQLAlchemy 1.4.x
- Some deprecation warnings when using legacy syntax
- Limited `use_insertmanyvalues` optimization

### SQLAlchemy 2.0.x
- Legacy `select([columns])` syntax shows deprecation warnings
- Some minor performance improvements over 1.4



## Recommendations

### For New Projects
- **Use SQLAlchemy 2.0.x** for best performance and latest features
- Use modern syntax throughout
- Enable all performance optimizations

### For Existing Projects
- **SQLAlchemy 1.4.x** is fully supported and stable
- **Upgrade to 2.0+** when ready for performance benefits
- Migration is straightforward with minimal code changes

### For Production
- **Any supported version** works reliably
- **2.0+** recommended for new deployments
- **1.4.x** fine for existing stable deployments