# Align Migration Roadmap

## Purpose

Align is moving incrementally from a Python/Shiny application to a React +
TypeScript frontend backed by FastAPI. Each milestone must leave the existing
application usable, retain Python as the source of deterministic financial
calculations, and introduce PostgreSQL feature-by-feature.

## Non-Negotiable Boundaries

- PostgreSQL is the persistent source of truth; simulations and projections are
  saved model snapshots, not transactions.
- Python owns calculations, validation, normalization, and persistence rules.
- React owns presentation, interaction, client state, and visualizations.
- User-defined categories are data, never fixed schema columns.
- LLMs and agents may interpret data but never become the source of truth or
  calculate authoritative financial results.
- Credentials are supplied only through environment variables and are never
  committed.
- Database migrations are reviewed and explicitly applied outside application
  startup.

## Current Baseline

- Shiny remains the current application entry point in `app.py`.
- The cash-flow numeric-input focus regression is fixed: changing a monthly
  field no longer recreates the active input.
- Deterministic cash-flow projection logic, request validation, and saved-run
  services are framework-independent Python with unit tests.
- Saved-run PostgreSQL migration and persistence code exist but the migration
  remains unapplied.
- Gas Sheet exports flow through validation, deduplication, derived analytics,
  and the existing dashboard CSV without modifying the source export.
- A deterministic vehicle TCO foundation separates observed costs from explicit
  assumptions; vehicle-source ingestion is not yet available in the repository.
- FastAPI and its test client cannot currently be installed in this worker
  environment because the configured package registry returns HTTP 403.

## Milestones

### Version 1 — Backend Foundation

Status: **in progress**

- [x] Extract the existing deterministic cash-flow projection loop into a pure Python service with regression tests
- [x] Fix the cash-flow numeric-input focus loss caused by reactive input replacement
- [x] Add framework-independent request contracts and cash-flow application services
- [ ] Add a minimal FastAPI application package
- [ ] Add a tested `GET /api/health` endpoint
- [x] Establish API-core testing conventions without database access
- [x] Add configuration boundaries for environment-derived settings
- [x] Audit direct Python runtime dependencies and ignore virtual environments and secrets
- [x] Add `./run` for transparent `.venv` setup and test execution
- [x] Keep Shiny entrypoints syntax-checked while migration continues

### Version 2 — React Foundation

- [ ] Add a separate React + TypeScript application
- [ ] Establish routing, application shell, navigation, and design tokens
- [ ] Add loading, error, and empty-state patterns
- [ ] Connect only to the health endpoint initially
- [ ] Keep the Shiny UI available during transition

### Version 3 — Cash Flow API and UI

- [x] Extract simulator inputs and deterministic projection logic behind a Python service boundary
- [ ] Add cash-flow calculation and saved-run HTTP API endpoints
- [ ] Migrate the cash-flow page to React without duplicating calculations
- [ ] Add scenario history and run-detail views
- [ ] Apply the saved-run migration only after explicit approval

### Version 4 — Gas Data

- [x] Replace script-only processing with a validated, traceable file pipeline
- [x] Normalize source dates, numbers, missing values, and duplicate observations with tests
- [x] Parse multi-header Sheet exports and preserve physical source-row traceability
- [x] Flag questionable intervals and exclude unreliable metrics without inventing corrections
- [ ] Add database persistence feature-by-feature
- [ ] Rebuild gas analytics and mobile-friendly gas entry in React
- [x] Auto-prepare current Sheet exports and support direct dashboard CSV import
- [x] Retain source row, raw-source fields, and stable source fingerprints during normalization

### Version 5 — Vehicles

- [ ] Define a plugin-owned vehicle data model
- [ ] Add vehicle, odometer, and ownership-event ingestion
- [ ] Distinguish observed events from assumptions and forecasts
- [x] Add normalized maintenance, repair, insurance, registration, tire, and
      fuel history
- [x] Add explicitly confirmed, database-audited vehicle and cost record editing/deletion

### Version 6 — Vehicle TCO

- [x] Implement deterministic Python total-cost-of-ownership calculations
- [ ] Support historical analysis, forecasts, and scenario comparison
- [ ] Add TCO API endpoints and React views
- [ ] Cover calculations with unit tests and explicit assumptions

### Version 7 — Finance Agent

- [ ] Define approved read-only data views and audit boundaries
- [ ] Add Finance Agent orchestration without write authority by default
- [ ] Support saved-model explanation and historical-scenario questions
- [ ] Keep model selection and interpretation separate from calculation

### Version 8 — Cohesive UI Modernization

- [ ] Complete responsive application shell and navigation
- [ ] Standardize tables, forms, cards, visual hierarchy, accessibility, and
      mobile behavior
- [ ] Retire Shiny only after equivalent React routes are verified

## Next Concrete Task

Run the Shiny application with `./run`, import a current gas Sheet CSV from
the Gas page, and verify the charts against the quality summary. Configure a
least-privilege local PostgreSQL URL in the gitignored `.env` file to enable
vehicle persistence; do not apply migrations without explicit approval.
