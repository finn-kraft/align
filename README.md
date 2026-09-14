# Align

Align is a data-driven personal financial modeling and decision-support
application. It currently provides a Shiny cash-flow simulator, gas analytics,
and a vehicle total-cost-of-ownership tracker.

## Current implementation

- Shiny remains the working application entry point
- Cash-flow scenarios can be saved as immutable PostgreSQL model snapshots
- Asset Modeling tracks vehicles and separately records purchase, maintenance,
  repairs, administrative costs, fuel, and other ownership costs
- Individual maintenance services such as oil changes and tires are grouped;
  repairs stay separate for clear review
- Google Sheets remains an input source for gas data; it is not canonical data

## Start Align

```bash
git clone <repository-url>
cd align
./run
```

You should not need to activate a virtual environment or run `pip install`
yourself. `./run` creates `.venv`, verifies its packages every time, and repairs
the environment automatically if installation was incomplete.

```bash
./run                 # Start the Shiny app
./run test            # Run the Python test suite
./run doctor          # Verify package installation
./run install         # Force a dependency reinstall
./run gas --input "/path/to/export.csv" --vehicle Jetta
```

The Gas dashboard automatically prepares `gas/data/live_data.csv` when it
is newer than the derived analytics file. A Sheet CSV can also be imported
directly from the dashboard; `./run gas --input ...` remains available for
command-line imports.

The gas import accepts Google Sheet CSV exports even when report/formula rows
appear above the actual headers. It preserves physical source-row numbers,
writes dashboard data to `gas/data/processed_data.csv`, and records fatal
rejects in `gas/data/rejected_rows.csv`. Questionable observations remain
visible with quality flags; unreliable MPG or cost-per-mile values are excluded
from their respective summaries instead of being silently corrected.

If creating `.venv` fails on Ubuntu/Debian, install the operating-system
package once with `sudo apt install python3-venv`, then run `./run` again.

## Database setup

`ALIGN_DATABASE_URL` must be supplied outside source control and use a
dedicated least-privilege application role. For local development, put it in
the gitignored repository-level `.env` file and `./run` will load it
automatically:

```dotenv
ALIGN_DATABASE_URL=postgresql://align_app:password@localhost/align
```

Never commit that file or use an owner/superuser credential. The application
keeps Asset Modeling viewable when the variable is absent, but disables
persistent vehicle creation until it is configured.

The application never runs migrations. Set a temporary
`ALIGN_MIGRATION_DATABASE_URL` for a separate migration-capable role, then
review and apply migrations only after approval:

```bash
psql "$ALIGN_MIGRATION_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0001_create_cashflow_saved_runs.sql
psql "$ALIGN_MIGRATION_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0002_create_vehicle_ownership.sql
psql "$ALIGN_MIGRATION_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0003_vehicle_record_management.sql
psql "$ALIGN_MIGRATION_DATABASE_URL" -v ON_ERROR_STOP=1 \
  -v align_runtime_role=YOUR_APP_ROLE \
  -f db/migrations/0004_grant_vehicle_runtime_permissions.sql
```

Migration 0003 installs database-enforced vehicle edit/delete auditing.
Migration 0004 grants the named runtime role only `SELECT`, `INSERT`,
`UPDATE`, and `DELETE` on vehicle records plus read access to the audit log. It must not be a superuser, owner, or
migration role.

See [Vehicle Ownership Tracking](docs/vehicle-ownership.md) for what to record
and how each category contributes to total cost of ownership.

## Layout

- `app.py` — current Shiny application entry point
- `cashflow/` — cash-flow projection and saved-run code
- `assets/` — vehicle ownership models, persistence, and Shiny UI
- `gas/` — legacy Google Sheet ingestion and gas analytics
- `db/migrations/` — reviewed, unapplied PostgreSQL migrations
- `tests/` — Python unit tests
- `docs/` — architecture and feature documentation
