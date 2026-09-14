# Align

Align is a data-driven personal financial modeling and decision-support
application. It currently provides a Shiny cash-flow simulator and gas
analytics while the project incrementally builds a React + TypeScript and
FastAPI architecture around the same deterministic Python financial models.

## Current implementation

- Shiny remains the working application entry point
- Cash-flow projection logic is framework-independent Python with regression
  tests
- Cash-flow scenarios can be explicitly saved as immutable PostgreSQL model
  snapshots when `ALIGN_DATABASE_URL` is configured and the reviewed migration
  has been applied
- The backend core contains validated request contracts and services ready for
  a FastAPI transport layer
- Google Sheets remains an input source for gas data; it is not canonical data

React, a running FastAPI transport, vehicle ingestion, and TCO features are
planned work. See [docs/roadmap.md](docs/roadmap.md) for actual status.

## Quick start

```bash
git clone <repository-url>
cd align
./run
```

The launcher creates `.venv`, installs the dependencies when `requirements.txt`
changes, and starts Shiny. Shell activation is not required.

Run the test suite with:

```bash
./run test
```

## Configuration and secrets

`ALIGN_DATABASE_URL` is the only database connection setting. It must contain
the credentials for a dedicated least-privilege application role; never put it
in source control. The saved-run migration is in
`db/migrations/0001_create_cashflow_saved_runs.sql` and is never run by the
application or launcher.

Google OAuth credentials and tokens belong in `gas/.env/`, which is ignored by
Git. See the gas ingestion code before configuring a Sheet source.

## Layout

- `app.py` — current Shiny application entry point
- `cashflow/` — deterministic projection, saved-run, and Shiny adapter code
- `backend/` — framework-independent API contracts and application services
- `gas/` — legacy Google Sheet ingestion and gas analytics
- `db/migrations/` — reviewed, unapplied PostgreSQL migrations
- `tests/` — Python unit tests
- `docs/` — architecture, canonical model, and migration roadmap

## Development notes

Python owns calculations, validation, normalization, and persistence rules.
React will own presentation and interaction as pages are migrated. Financial
categories remain data, not database columns; cash-flow scenarios are model
runs, not canonical ledger transactions.
