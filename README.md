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
```

If creating `.venv` fails on Ubuntu/Debian, install the operating-system
package once with `sudo apt install python3-venv`, then run `./run` again.

## Database setup

`ALIGN_DATABASE_URL` must be supplied outside source control and use a
dedicated least-privilege application role. The application never runs
migrations. Review and apply them with a separate migration role:

```bash
psql "$ALIGN_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0001_create_cashflow_saved_runs.sql
psql "$ALIGN_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0002_create_vehicle_ownership.sql
psql "$ALIGN_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/migrations/0003_vehicle_record_management.sql
```

The runtime role uses `SELECT, INSERT` for normal operation. Migration 0003
adds narrowly scoped `UPDATE, DELETE` rights for vehicle records and installs
database-enforced edit/delete auditing. It must not be a superuser, owner, or
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
