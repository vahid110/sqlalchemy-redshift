#!/bin/bash
# Compare GitHub repo (sqlalchemy2) with Internal repo (mainline)

GITHUB_REPO="/Users/vahidsbr/sqlalchemy/sqlalchemy-redshift"
INTERNAL_REPO="/Users/vahidsbr/sqlalchemy/Sqlalchemy-amazon-redshift"

echo "=== Comparing Core Files ==="
echo ""

# Compare dialect.py
echo "1. sqlalchemy_redshift/dialect.py"
diff -u "$INTERNAL_REPO/sqlalchemy_redshift/dialect.py" "$GITHUB_REPO/sqlalchemy_redshift/dialect.py" | head -100

echo ""
echo "=== Files only in GitHub repo (sqlalchemy2) ==="
cd "$GITHUB_REPO"
git diff --name-only main..sqlalchemy2 | while read file; do
    if [ ! -f "$INTERNAL_REPO/$file" ]; then
        echo "  NEW: $file"
    fi
done

echo ""
echo "=== Summary ==="
echo "GitHub repo (sqlalchemy2): $(cd $GITHUB_REPO && git rev-parse --short sqlalchemy2)"
echo "Internal repo (mainline): $(cd $INTERNAL_REPO && git rev-parse --short mainline)"
