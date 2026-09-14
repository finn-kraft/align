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

Vehicle and cost records can be corrected or deleted. PostgreSQL records the
previous row in `vehicle_record_audit` for every update or deletion. Normal
vehicle deletion is blocked while costs exist; **Delete All Vehicle Data**
requires typing the vehicle name exactly and removes the vehicle and costs in
one transaction.

## First-time setup

1. Apply `db/migrations/0002_create_vehicle_ownership.sql` with the migration role.
2. Apply `db/migrations/0003_vehicle_record_management.sql` to enable audited record management.
3. Set `ALIGN_DATABASE_URL` outside the repository, run `./run`, add a vehicle, and record costs.

The application never runs migrations and does not need a superuser or owner credential.
