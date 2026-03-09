"""
Sample application demonstrating typical customer usage of sqlalchemy-redshift.

This app shows:
  - Engine creation with the recommended redshift_connector dialect
  - Table definition with Redshift-specific DDL options (diststyle, distkey, sortkey, encode)
  - Core CRUD operations
  - COPY from S3 and UNLOAD to S3 via the library's command helpers
  - Schema reflection
  - Alembic migration (optional, shown as a snippet)

Run:
    pip install -r requirements.txt
    python app.py

Environment variables required:
    REDSHIFT_HOST       - Redshift cluster endpoint
    REDSHIFT_PORT       - Default 5439
    REDSHIFT_USER       - Database user
    REDSHIFT_PASSWORD   - Database password
    REDSHIFT_DB         - Database name
    REDSHIFT_IAM_ROLE   - IAM role ARN attached to the cluster (for COPY/UNLOAD)
    S3_BUCKET           - S3 bucket name used for COPY/UNLOAD
"""

import os
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy_redshift.dialect import (
    CopyCommand, UnloadFromSelect, Format,
    CreateMaterializedView, RefreshMaterializedView, DropMaterializedView,
)

# ---------------------------------------------------------------------------
# 1. Engine
# ---------------------------------------------------------------------------
REDSHIFT_URL = (
    "redshift+redshift_connector://{user}:{password}@{host}:{port}/{db}"
).format(
    user=os.environ["REDSHIFT_USER"],
    password=os.environ["REDSHIFT_PASSWORD"],
    host=os.environ["REDSHIFT_HOST"],
    port=os.environ.get("REDSHIFT_PORT", "5439"),
    db=os.environ["REDSHIFT_DB"],
)

engine = sa.create_engine(
    REDSHIFT_URL,
    # Connection pool tuned for typical analytics workloads
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,          # detect stale connections
    connect_args={"sslmode": "verify-full"},
)

# ---------------------------------------------------------------------------
# 2. Schema definition with Redshift-specific options
# ---------------------------------------------------------------------------
metadata = sa.MetaData()

orders = sa.Table(
    "orders",
    metadata,
    sa.Column("order_id",   sa.Integer,     primary_key=True),
    sa.Column("customer_id",sa.Integer,     nullable=False),
    sa.Column("amount",     sa.Numeric(12, 2)),
    sa.Column("status",     sa.String(32),  redshift_encode="lzo"),
    sa.Column("created_at", sa.DateTime),
    # Redshift distribution / sort options
    redshift_diststyle="KEY",
    redshift_distkey="customer_id",
    redshift_sortkey="created_at",
)

# ---------------------------------------------------------------------------
# 3. DDL – create / drop
# ---------------------------------------------------------------------------
def setup_schema():
    metadata.create_all(engine)
    print("Schema created.")

def teardown_schema():
    metadata.drop_all(engine)
    print("Schema dropped.")

# ---------------------------------------------------------------------------
# 4. Core CRUD
# ---------------------------------------------------------------------------
def insert_rows():
    with engine.begin() as conn:
        conn.execute(orders.insert(), [
            {"order_id": 1, "customer_id": 42, "amount": 99.99,  "status": "NEW"},
            {"order_id": 2, "customer_id": 42, "amount": 149.00, "status": "SHIPPED"},
            {"order_id": 3, "customer_id": 7,  "amount": 9.99,   "status": "NEW"},
        ])
    print("Rows inserted.")

def query_rows():
    with engine.connect() as conn:
        result = conn.execute(
            sa.select(orders).where(orders.c.customer_id == 42)
        )
        for row in result:
            print(row)

def update_row():
    with engine.begin() as conn:
        conn.execute(
            orders.update()
            .where(orders.c.order_id == 1)
            .values(status="PROCESSED")
        )
    print("Row updated.")

def delete_row():
    with engine.begin() as conn:
        conn.execute(orders.delete().where(orders.c.order_id == 3))
    print("Row deleted.")

# ---------------------------------------------------------------------------
# 5. Bulk load from S3 (COPY) and export to S3 (UNLOAD)
# ---------------------------------------------------------------------------
IAM_ROLE = os.environ["REDSHIFT_IAM_ROLE"]
S3_BUCKET = os.environ["S3_BUCKET"]

def copy_from_s3():
    """Load CSV data from S3 into the orders table."""
    copy_cmd = CopyCommand(
        to=orders,
        data_location=f"s3://{S3_BUCKET}/data/orders/",
        iam_role_arns=IAM_ROLE,
        format=Format.csv,
        ignore_header=1,
        region="us-east-1",
    )
    with engine.begin() as conn:
        conn.execute(copy_cmd)
    print("COPY from S3 complete.")

def unload_to_s3():
    """Export query results to S3 as Parquet."""
    select_stmt = sa.select(orders).where(orders.c.status == "NEW")
    unload_cmd = UnloadFromSelect(
        select=select_stmt,
        unload_location=f"s3://{S3_BUCKET}/exports/new_orders/",
        iam_role_arns=IAM_ROLE,
        format=Format.parquet,
        allow_overwrite=True,
    )
    with engine.begin() as conn:
        conn.execute(unload_cmd)
    print("UNLOAD to S3 complete.")

# ---------------------------------------------------------------------------
# 6. Materialized view lifecycle
# ---------------------------------------------------------------------------
def materialized_view_demo():
    mv_select = sa.select(
        orders.c.customer_id,
        sa.func.sum(orders.c.amount).label("total_spent"),
    ).group_by(orders.c.customer_id)

    with engine.begin() as conn:
        conn.execute(CreateMaterializedView("customer_totals", mv_select))
        conn.execute(RefreshMaterializedView("customer_totals"))
        conn.execute(DropMaterializedView("customer_totals"))
    print("Materialized view lifecycle complete.")

# ---------------------------------------------------------------------------
# 7. Schema reflection
# ---------------------------------------------------------------------------
def reflect_schema():
    insp = inspect(engine)
    for table_name in insp.get_table_names(schema="public"):
        cols = insp.get_columns(table_name, schema="public")
        print(f"{table_name}: {[c['name'] for c in cols]}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    setup_schema()
    insert_rows()
    query_rows()
    update_row()
    delete_row()
    reflect_schema()
    # Uncomment when S3 / IAM role are configured:
    # copy_from_s3()
    # unload_to_s3()
    # materialized_view_demo()
    teardown_schema()
