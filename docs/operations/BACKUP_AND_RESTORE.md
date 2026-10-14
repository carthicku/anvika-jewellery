# Backup and Restore

## What needs backing up
| Data | Where | Backup method |
|------|-------|---------------|
| Database (orders, customers, products, payments, audit logs) | Supabase PostgreSQL | Supabase automatic daily backups (paid plans) **plus** our own weekly `pg_dump` kept off-platform |
| Product images | S3-compatible bucket | Bucket versioning or a periodic `rclone sync` to a second provider |
| Secrets | Hosting secret store + password manager | Kept in the owner's password manager (never in Git) |
| Code | Git remote (GitHub) | The remote itself, plus a local clone |

The VM itself holds no unique data, so it can be rebuilt from Git and secrets.

## Supabase backups
* Free plan: **no** automatic backups available for download. Rely on the manual `pg_dump` below.
* Pro plan and above: daily backups. Point-in-time recovery (PITR) is an add-on and recommended
  once real orders flow. Confirm the current plan details on Supabase's pricing page before launch.

## Manual logical backup (weekly, and before every migration)
Requires the PostgreSQL 17 client tools (`pg_dump`). On Windows, the embedded-postgres package
includes them under `node_modules/@embedded-postgres/windows-x64/native/bin/`.
```bash
# Use the session-pooler or direct connection string (plain postgresql:// prefix, not +psycopg)
pg_dump "postgresql://postgres.<ref>:<password>@<host>:5432/postgres?sslmode=require" \
  --format=custom --no-owner --no-privileges --schema=public \
  --file=backup-$(date +%Y%m%d-%H%M).dump
```
Store the dump encrypted (e.g. in a 7-Zip AES-256 archive or an encrypted cloud folder). It contains
personal data.

## Restore (test this quarterly on a scratch database, never first on production)
```bash
createdb -h 127.0.0.1 -p 54329 -U postgres restore_check
pg_restore -h 127.0.0.1 -p 54329 -U postgres -d restore_check --no-owner backup-YYYYMMDD-HHMM.dump
# Point a local backend at restore_check and run: python -m app.cli verify-integrity
```
`verify-integrity` (Phase 8) checks the order totals against the line items, the inventory ledger
against the levels, and that every paid order has a captured payment attempt.

Restoring production:
1. Put the store in maintenance mode (Caddy serves a maintenance page; webhooks will be retried by
   Razorpay for a while).
2. Restore into a **new** database/project, verify, then switch `DATABASE_URL`.
3. Reconcile payments captured during the outage window using the Razorpay dashboard and
   `python -m app.cli reconcile-payments --since <timestamp>`.

## Data retention
| Data | Retention (proposal — owner/legal to confirm) |
|------|-----------------------------------------------|
| Orders, invoices, payments | As required by Indian tax law (commonly 8 years for GST records — **confirm with a CA**) |
| Audit logs | 3 years |
| Revoked/expired sessions, used tokens | Purged after 30 days (`run-jobs` housekeeping) |
| Contact enquiries | 2 years |
| Rate-limit buckets | Purged hourly |
| Dev email sink | Local only, delete freely |
