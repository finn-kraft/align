-- Vehicle ownership records are asset-model inputs, not canonical ledger rows.
-- Apply manually with a migration-capable role.
BEGIN;

CREATE TABLE IF NOT EXISTS vehicles (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (btrim(name) <> ''),
    make text,
    model text,
    year integer CHECK (year IS NULL OR year BETWEEN 1886 AND 9999),
    acquired_on date NOT NULL,
    starting_odometer numeric(12, 1) CHECK (starting_odometer IS NULL OR starting_odometer >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vehicle_cost_events (
    id uuid PRIMARY KEY,
    vehicle_id uuid NOT NULL REFERENCES vehicles(id),
    occurred_on date NOT NULL,
    cost_category text NOT NULL CHECK (cost_category IN ('purchase', 'maintenance', 'repair', 'administrative', 'fuel', 'other')),
    service_type text NOT NULL CHECK (btrim(service_type) <> ''),
    description text,
    amount numeric(14, 2) NOT NULL CHECK (amount >= 0),
    odometer numeric(12, 1) CHECK (odometer IS NULL OR odometer >= 0),
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS vehicle_cost_events_vehicle_date_idx
    ON vehicle_cost_events (vehicle_id, occurred_on DESC, id DESC);
CREATE INDEX IF NOT EXISTS vehicle_cost_events_vehicle_category_idx
    ON vehicle_cost_events (vehicle_id, cost_category, service_type);

COMMIT;
