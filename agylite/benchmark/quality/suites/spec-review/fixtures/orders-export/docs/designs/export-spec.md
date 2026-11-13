# Nightly orders export

## Goal

Every night, write each tenant's orders from the last 24 hours to a CSV file in object storage, so finance teams can
load them into their own tools.

## Design

1. A scheduled job runs at 02:00 UTC.
2. Exports are sharded by tenant tier: each shard runs as its own job.
3. For each tenant, the job reads orders with the existing `listOrders(tenantId, { since })`, which already pages
   through results 500 orders at a time, so memory stays flat for large tenants.
4. Rows are written as CSV with exactly these columns, in this order: `order_id`, `created_at` (ISO 8601, UTC),
   `currency` (ISO 4217 code), `total_cents` (integer), `status` (one of `paid`, `refunded`, `void`).
5. The file is uploaded with `putObject` to `exports/<tenantId>/<YYYY-MM-DD>.csv`.
6. If an upload fails, choose an appropriate retry strategy.

## Out of scope

Exports on demand; formats other than CSV.
