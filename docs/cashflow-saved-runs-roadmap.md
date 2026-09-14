# Cash-Flow Saved Runs Roadmap

## Current State

The Shiny app in `app.py` mounts the cash-flow module from
`cashflow/cashflow.py`. The simulator:

1. collects global settings and per-month inputs in the UI;
2. builds an in-memory state object;
3. calculates the projection only after **Run Simulation** is selected; and
4. writes a single replaceable local JSON scenario on **Save Scenario**.

The local-save path is not present in the tracked repository, so it must be
treated as development state rather than a database migration source. No
canonical transaction or ledger tables are currently implemented in this
repository. The saved-run feature must therefore be isolated from source
financial data.

## Saved-Run Data Contract

Saved runs belong to the cash-flow forecasting module, not the canonical
ledger. The initial migration will create two plugin-owned tables:

### `cashflow_saved_runs`

One immutable snapshot per explicit user save.

| Column | Purpose |
| --- | --- |
| `id uuid primary key` | Stable run identifier |
| `created_at timestamptz` | Auditable save time |
| `model_version text` | Projection/calculation contract version |
| `name text` | User-facing run name |
| `notes text` | Optional scenario description |
| `start_date date` | First projected month, normalized to its first day |
| `month_count integer` | Number of projected months |
| `starting_cash numeric(14,2)` | Opening cash balance |
| `apy numeric(9,6)` | Annual percentage yield assumed by the model |
| `assumptions jsonb` | Complete recurring and other flexible input snapshot |
| `created_by text nullable` | Future-compatible actor identifier |
| `source_run_id uuid nullable` | Optional ancestry when a run is duplicated later |

`assumptions` stores dynamic categories and labels as data, never as schema
columns. It will include the recurring assumptions and the complete set of
per-month user inputs required to reproduce the calculation.

### `cashflow_saved_run_months`

One immutable projected result per saved run and month.

| Column | Purpose |
| --- | --- |
| `saved_run_id uuid` | Foreign key to `cashflow_saved_runs` |
| `month_index smallint` | Zero-based sequence in the projection |
| `month_start date` | Projected calendar month |
| `income numeric(14,2)` | Projected income |
| `interest_income numeric(14,2)` | Interest projected by the model |
| `recurring_expense numeric(14,2)` | Sum of recurring assumptions |
| `variable_expense numeric(14,2)` | Sum of non-recurring inputs |
| `net_change numeric(14,2)` | Monthly net change |
| `ending_cash numeric(14,2)` | Projected ending balance |
| `expense_categories jsonb` | Dynamic category/amount snapshot |
| `primary key (saved_run_id, month_index)` | One result for each month in a run |

The parent row keeps the exact inputs; child rows make comparisons and
month-oriented reporting efficient while retaining flexible categories in
JSONB. Both tables will be append-only for this feature. Updating or deleting
a run is deliberately out of scope.

## Database Safety

The application will read its connection string only from
`ALIGN_DATABASE_URL`; credentials will not be stored in source control.
Deployment must use a dedicated application role, not the database owner or a
superuser. Its initial grants should be limited to:

- `USAGE` on the schema
- `SELECT, INSERT` on these two saved-run tables
- `USAGE, SELECT` on any sequence required by the migration

The migration itself must be applied by the existing migration/deployment
process using a separate migration-capable role. It will not touch transactions
or other source-of-truth financial records.

## Delivery Checklist

- [x] Inspect the current UI, forecast flow, and canonical data model
- [x] Define the saved-run schema and role boundary
- [x] Create a dedicated worker branch
- [x] Commit this roadmap and data contract
- [x] Add migration tooling and an additive saved-run migration
- [x] Extract a versioned, testable projection snapshot builder
- [x] Add repository tests for serialization and PostgreSQL persistence
- [x] Replace the local Save Scenario action with explicit **Save Run** UI
- [x] Add a run name and optional notes without changing calculations
- [x] Apply focused Cash Flow visual cleanup: settings grouping, action hierarchy,
      clearer section labels, and consistent spacing
- [x] Run the full test suite after each executable change
- [x] Update this checklist and open a reviewable pull request

## First UI Changes

The first UI pass will preserve every existing control and calculation. It will
rename **Save Scenario** to **Save Run**, separate primary actions from loading,
and group model settings, recurring assumptions, and projection actions more
clearly. Visual changes will follow only after the persistence contract and
tests are in place.

## Verification

- The saved-run module and repository tests pass with
  `PYTHONPATH=. python -m unittest discover -s tests -v` (4 tests).
- `cashflow/cashflow.py` passes Python syntax validation.
- The PostgreSQL migration is committed only. It has not been applied to any
  database.
