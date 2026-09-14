-- Grant only the permissions required by vehicle ownership workflows.
-- Apply with psql -v align_runtime_role=YOUR_APP_ROLE using a migration-capable
-- connection. Do not use the runtime application connection for migrations.
\if :{?align_runtime_role}
\else
\echo 'align_runtime_role is required'
\quit 3
\endif

BEGIN;

GRANT USAGE ON SCHEMA public TO :"align_runtime_role";
GRANT SELECT, INSERT, UPDATE, DELETE
    ON TABLE vehicles, vehicle_cost_events
    TO :"align_runtime_role";
GRANT SELECT
    ON TABLE vehicle_record_audit
    TO :"align_runtime_role";

COMMIT;
