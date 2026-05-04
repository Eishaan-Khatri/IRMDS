# IRMDS Task Checklist

This is a working checklist, not a promise that everything is production-ready.

## v0 Complete

- [x] Project scaffold
- [x] `pyproject.toml`, dependencies, `.gitignore`, `.env.example`, MIT license
- [x] Pydantic settings
- [x] Structured logging
- [x] Custom exceptions
- [x] Threaded `BaseModule` contract
- [x] Plugin discovery
- [x] Event bus with history and filters
- [x] Metrics collector
- [x] Alert manager with cooldown, deduplication, escalation, and SQLite path
- [x] Session lifecycle
- [x] SQLAlchemy database setup
- [x] Visual module
- [x] Network module
- [x] Finance/time-series module
- [x] Infrastructure module
- [x] FastAPI routes for system, modules, alerts, metrics, sessions, export, WebSocket
- [x] Dry-run `CommandBus`
- [x] Simulated `ActuationGateway`
- [x] `/commands` API
- [x] Streamlit dashboard shell and visual/dashboard components
- [x] Deterministic sample data generator
- [x] Unit and integration tests
- [x] README/docs synced to v0 scope

## v0 Verification Gate

- [x] `ruff check .`
- [x] `mypy core api modules`
- [x] `pytest tests -q`
- [x] `python -m compileall -q api core modules dashboard cli notifications tests scripts`
- [x] `git diff --check`

## v1 Next

- [ ] Dockerfile for API
- [ ] Dockerfile for dashboard
- [ ] Docker Compose
- [ ] GitHub Actions CI
- [ ] Typer CLI
- [ ] Notification manager
- [ ] Console notifier
- [ ] Slack notifier
- [ ] Discord notifier
- [ ] Email notifier
- [ ] Dashboard overview page
- [ ] Dashboard network page
- [ ] Dashboard finance page
- [ ] Dashboard infrastructure page
- [ ] Dashboard alert table/export page
- [ ] Prometheus metrics endpoint
- [ ] Contributor guide
- [ ] Module starter template

## v2 Candidates

- [ ] Policy engine
- [ ] Authentication and RBAC
- [ ] Append-only audit ledger
- [ ] Digital twin or command simulation harness
- [ ] Distributed event bus adapter
- [ ] Model registry and drift detection
- [ ] Real actuation adapters behind explicit safety gates
