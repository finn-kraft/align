-- Audited vehicle record editing and deletion.
-- Apply manually with the migration-capable role after migration 0002.
BEGIN;

CREATE TABLE IF NOT EXISTS vehicle_record_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    changed_at timestamptz NOT NULL DEFAULT now(),
    changed_by text NOT NULL DEFAULT session_user,
    action text NOT NULL CHECK (action IN ('UPDATE', 'DELETE')),
    record_type text NOT NULL CHECK (record_type IN ('vehicle', 'vehicle_cost_event')),
    record_id uuid NOT NULL,
    vehicle_id uuid NOT NULL,
    previous_record jsonb NOT NULL,
    replacement_record jsonb
);

CREATE OR REPLACE FUNCTION audit_vehicle_record_change()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    affected_vehicle_id uuid;
    affected_record_id uuid;
    affected_record_type text;
BEGIN
    affected_record_type := CASE TG_TABLE_NAME
        WHEN 'vehicles' THEN 'vehicle'
        ELSE 'vehicle_cost_event'
    END;
    affected_record_id := OLD.id;
    affected_vehicle_id := CASE TG_TABLE_NAME
        WHEN 'vehicles' THEN OLD.id
        ELSE OLD.vehicle_id
    END;

    INSERT INTO vehicle_record_audit
        (changed_by, action, record_type, record_id, vehicle_id, previous_record, replacement_record)
    VALUES
        (session_user, TG_OP, affected_record_type, affected_record_id, affected_vehicle_id,
         to_jsonb(OLD), CASE WHEN TG_OP = 'UPDATE' THEN to_jsonb(NEW) ELSE NULL END);

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS vehicles_audit_update_delete ON vehicles;
CREATE TRIGGER vehicles_audit_update_delete
AFTER UPDATE OR DELETE ON vehicles
FOR EACH ROW EXECUTE FUNCTION audit_vehicle_record_change();

DROP TRIGGER IF EXISTS vehicle_cost_events_audit_update_delete ON vehicle_cost_events;
CREATE TRIGGER vehicle_cost_events_audit_update_delete
AFTER UPDATE OR DELETE ON vehicle_cost_events
FOR EACH ROW EXECUTE FUNCTION audit_vehicle_record_change();

-- Runtime grants are role-specific and are applied by migration 0004.

COMMIT;
