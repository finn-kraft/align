# Align Backend Core

`backend/align_api` currently contains framework-independent configuration,
request contracts, and cash-flow application services. It deliberately does
not connect to PostgreSQL at import time.

The FastAPI transport layer will be added when its dependencies can be
installed and exercised in the development environment. It will adapt these
services rather than duplicate financial calculations.
