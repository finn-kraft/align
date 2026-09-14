# Vehicle Ownership Tracking

The Asset Modeling tab records observed vehicle costs so Align can calculate
total cost of ownership from real events rather than a generic estimate.

| Category | Examples | How it appears |
| --- | --- | --- |
| Purchase | vehicle purchase price | included automatically when the vehicle is created |
| Maintenance | oil changes, tires, brakes, scheduled service | grouped individually by service type |
| Repair | diagnostic work, failed components, accident repair | shown in a separate repairs table |
| Administrative | insurance, registration, inspection, property tax | separate total-cost category |
| Fuel | fuel purchases not yet imported from the gas workflow | separate total-cost category |
| Other | parking, tolls, accessories | separate total-cost category |

Every cost is append-only. If an entry is wrong, record a correcting entry for
now; editing/deleting history is deferred until an audited review workflow
exists.

## First-time setup

1. Apply `db/migrations/0002_create_vehicle_ownership.sql` with the migration role.
2. Give the runtime Align role `SELECT, INSERT` on `vehicles` and `vehicle_cost_events`.
3. Set `ALIGN_DATABASE_URL` outside the repository, run `./run`, add a vehicle, and record costs.

The application never runs migrations and does not need a superuser or owner credential.
