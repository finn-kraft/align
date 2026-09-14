-- Cash-flow saved runs are model snapshots. This migration does not touch
-- canonical transactions, accounts, categories, or any other source data.
BEGIN;

CREATE TABLE IF NOT EXISTS cashflow_saved_runs (
    id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    model_version text NOT NULL,
    name text NOT NULL CHECK (btrim(name) <> ''),
    notes text,
    start_date date NOT NULL,
    month_count integer NOT NULL CHECK (month_count > 0),
    starting_cash numeric(14, 2) NOT NULL,
    apy numeric(9, 6) NOT NULL,
    assumptions jsonb NOT NULL,
    created_by text,
    source_run_id uuid REFERENCES cashflow_saved_runs(id),
    CHECK (jsonb_typeof(assumptions) = 'object')
);

CREATE TABLE IF NOT EXISTS cashflow_saved_run_months (
    saved_run_id uuid NOT NULL REFERENCES cashflow_saved_runs(id),
    month_index smallint NOT NULL CHECK (month_index >= 0),
    month_start date NOT NULL,
    income numeric(14, 2) NOT NULL,
    interest_income numeric(14, 2) NOT NULL,
    recurring_expense numeric(14, 2) NOT NULL,
    variable_expense numeric(14, 2) NOT NULL,
    net_change numeric(14, 2) NOT NULL,
    ending_cash numeric(14, 2) NOT NULL,
    expense_categories jsonb NOT NULL,
    PRIMARY KEY (saved_run_id, month_index),
    CHECK (jsonb_typeof(expense_categories) = 'object')
);

CREATE INDEX IF NOT EXISTS cashflow_saved_runs_created_at_idx
    ON cashflow_saved_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS cashflow_saved_run_months_month_start_idx
    ON cashflow_saved_run_months (month_start);

COMMIT;
