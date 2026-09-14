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

- The Shiny application remains the running interface in `app.py`.
- Cash-flow calculations remain in `cashflow/cashflow.py`.
- An unapplied saved-run PostgreSQL migration and persistence layer already
  exist on this branch.
- Gas data is retrieved from a Google Sheet into CSV files, then processed by
  pandas; it is not yet canonical PostgreSQL data.
- No FastAPI, React, TypeScript, vehicle ingestion, or TCO implementation is
  present.

## Milestones

### Version 1 — Backend Foundation

Status: **in progress**

- [ ] Add a minimal FastAPI application package
- [ ] Add a tested `GET /api/health` endpoint
- [ ] Establish API testing conventions without database access
- [ ] Add configuration boundaries for environment-derived settings
- [ ] Keep Shiny operational throughout

### Version 2 — React Foundation

- [ ] Add a separate React + TypeScript application
- [ ] Establish routing, application shell, navigation, and design tokens
- [ ] Add loading, error, and empty-state patterns
- [ ] Connect only to the health endpoint initially
- [ ] Keep the Shiny UI available during transition

### Version 3 — Cash Flow API and UI

- [ ] Extract simulator inputs and deterministic projection logic behind a
      Python service boundary
- [ ] Add cash-flow calculation and saved-run API endpoints
- [ ] Migrate the cash-flow page to React without duplicating calculations
- [ ] Add scenario history and run-detail views
- [ ] Apply the saved-run migration only after explicit approval

### Version 4 — Gas Data

- [ ] Replace script-only ingestion with a validated, traceable pipeline
- [ ] Normalize dates, numbers, missing values, and duplicates
- [ ] Add database persistence feature-by-feature
- [ ] Rebuild gas analytics and mobile-friendly gas entry in React
- [ ] Retain source identifiers and raw-source traceability

### Version 5 — Vehicles

- [ ] Define a plugin-owned vehicle data model
- [ ] Add vehicle, odometer, and ownership-event ingestion
- [ ] Distinguish observed events from assumptions and forecasts
- [ ] Add normalized maintenance, repair, insurance, registration, tire, and
      fuel history

### Version 6 — Vehicle TCO

- [ ] Implement deterministic Python total-cost-of-ownership calculations
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

## Current Smallest Safe Task

Create a FastAPI application scaffold with a tested health endpoint. It must
not import Shiny, connect to PostgreSQL, execute migrations, change existing
cash-flow calculations, or alter financial data.
