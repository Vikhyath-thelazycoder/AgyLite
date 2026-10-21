# Billing service

Postgres table `invoices` has a `user_id` column. Since accounts became shared (one account, many users), every
invoice really belongs to an account. We want `account_id` everywhere: database column, API field, client SDK and
the 40+ call sites across `src/`.
