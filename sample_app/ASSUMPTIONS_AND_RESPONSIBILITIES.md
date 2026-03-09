# Sample Application – Assumptions & Shared Responsibility

## What this sample covers

`app.py` demonstrates the primary ways a customer would consume the
`sqlalchemy-redshift` Python library (a PyPI wheel / source distribution):

| Feature | API used |
|---|---|
| Engine creation | `sa.create_engine("redshift+redshift_connector://…")` |
| DDL with Redshift options | `redshift_diststyle`, `redshift_distkey`, `redshift_sortkey`, `redshift_encode` |
| Core CRUD | `Table.insert / select / update / delete` |
| Bulk load from S3 | `CopyCommand` |
| Bulk export to S3 | `UnloadFromSelect` |
| Materialized views | `CreateMaterializedView`, `RefreshMaterializedView`, `DropMaterializedView` |
| Schema reflection | `sqlalchemy.inspect(engine)` |

---

## Assumptions about the customer environment

| # | Assumption |
|---|---|
| 1 | Python 3.8+ is installed on the host running the application. |
| 2 | The host has outbound TCP access to the Redshift cluster endpoint on port 5439 (or a custom port). |
| 3 | `redshift_connector` (AWS native driver) is installed alongside this library. The library does **not** bundle a DBAPI driver. |
| 4 | An Amazon Redshift cluster (provisioned or Serverless) already exists and is reachable from the application host. |
| 5 | A database user with appropriate privileges (CREATE, INSERT, SELECT, UPDATE, DELETE, COPY, UNLOAD) exists. |
| 6 | For COPY/UNLOAD operations, an IAM role is attached to the Redshift cluster with `s3:GetObject` / `s3:PutObject` permissions on the target bucket. |
| 7 | SSL is enabled on the cluster (the library defaults to `sslmode=verify-full` and ships its own CA bundle). |
| 8 | Credentials are supplied via environment variables, not hard-coded. |
| 9 | The application runs in a network environment where the Redshift security group / VPC allows inbound connections from the application host. |
| 10 | For Alembic migrations, Alembic ≥ 1.0.6 is installed separately. |

---

## Shared responsibility model

### AWS / library responsibilities
- The `redshift_connector` driver enforces TLS and certificate verification by default.
- The library ships a bundled Redshift CA certificate (`redshift-ca-bundle.crt`) used for `verify-full` SSL validation.
- The library validates IAM role ARN and access key formats before issuing COPY/UNLOAD commands.
- AWS manages the underlying Redshift cluster infrastructure, patching, and availability.

### Customer responsibilities

**Credential management**
- Never hard-code passwords or AWS keys in source code.
- Use AWS Secrets Manager, Parameter Store, or IAM instance profiles / pod identity to inject credentials at runtime.
- Rotate database passwords and IAM access keys regularly.

**Network security**
- Restrict Redshift security group inbound rules to known application CIDRs only.
- Deploy the application and cluster in the same VPC where possible; use VPC endpoints for S3 to avoid public internet traffic during COPY/UNLOAD.

**IAM least privilege**
- Scope the IAM role attached to Redshift to only the specific S3 prefixes needed for COPY/UNLOAD.
- Grant database users only the privileges they need (avoid superuser for application accounts).

**Data encryption**
- Enable encryption at rest on the Redshift cluster (AWS KMS).
- Use the `encrypted=True` flag on `UnloadFromSelect` when writing sensitive data to S3.
- Ensure the target S3 bucket has server-side encryption enabled.

**Input validation**
- Validate and sanitize all user-supplied values before passing them into SQLAlchemy expressions to prevent SQL injection through dynamic query construction.
- Use SQLAlchemy bound parameters (the default) rather than string interpolation.

**Dependency management**
- Pin dependency versions in `requirements.txt` and audit them regularly with tools such as `pip-audit` or `safety`.
- Monitor the `sqlalchemy-redshift` and `redshift_connector` release channels for security patches.

**Connection pool hygiene**
- Set `pool_pre_ping=True` (shown in the sample) to detect and recycle stale connections.
- Size the pool (`pool_size`, `max_overflow`) to stay within the Redshift cluster's `max_connections` limit.

**Logging & monitoring**
- Do not log raw SQL that may contain credentials or PII.
- Enable Redshift audit logging and CloudTrail to capture data access events.
- Monitor `STL_LOAD_ERRORS` and `STL_UNLOAD_LOG` for COPY/UNLOAD failures.

**Penetration testing scope**
- Obtain written approval from AWS before conducting penetration tests against AWS-managed infrastructure (see https://aws.amazon.com/security/penetration-testing/).
- Tests should target the application layer (SQLAlchemy query construction, credential handling, connection configuration) and the customer-managed network controls, not the Redshift service itself.
