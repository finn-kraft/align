# Database Migrations

Migration files are ordered PostgreSQL DDL changes. They are deliberately
**not** run automatically by the application.

## Applying a migration

Only apply a migration after review and explicit approval. Use a
migration-capable deployment role, never the runtime application role:

```bash
psql "$ALIGN_DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f db/migrations/0001_create_cashflow_saved_runs.sql
```

The runtime application reads the same environment-variable name, but must use
a dedicated least-privilege role with only `USAGE` on the target schema and
`SELECT, INSERT` on the saved-run tables. It does not need DDL privileges.

## Safety rules

- Do not place credentials in migration files or source control.
- Do not apply migrations from application startup code.
- Do not modify canonical ledger/source-of-truth financial data in a
  cash-flow saved-run migration.
- Review a migration against the target database before applying it.
