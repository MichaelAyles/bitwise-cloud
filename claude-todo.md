# Claude TODO

Tasks for Claude to implement in upcoming sessions.

## Deployment Hardening

- [ ] Add Alembic migration guard — either a file lock or a dedicated init container to prevent race conditions if backend ever scales to multiple replicas
- [ ] Add `chmod 600 .env` check to the backup script or a startup healthcheck that warns if `.env` permissions are too open
- [ ] Add a `scripts/restore-postgres.sh` companion to the backup script with verification steps

## CI/CD

- [ ] Add linting step to GitHub Actions (black --check, mypy)
- [ ] Add `poetry run pytest` to CI before the Docker build step
- [ ] Consider caching Python dependencies in CI (pip cache or poetry cache layer)

## Backend

- [ ] Return HTTP 503 from `/api/health` when status is `"degraded"` (currently returns 200 regardless) so UptimeRobot catches dependency failures
- [ ] Add structured logging (JSON format) to backend and worker for easier log parsing
- [ ] Add request ID middleware for tracing requests across backend and worker

## Frontend

- [ ] Add health status indicator in the admin panel (poll `/api/health`)
- [ ] Add version/commit SHA display in the footer (inject at build time from `VITE_GIT_SHA`)

## MCP Plugin

- [ ] Add integration tests that exercise the full ingestion + search pipeline with a small test PDF
