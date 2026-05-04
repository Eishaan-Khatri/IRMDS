# IRMDS v0/v1 Plan

This document is the practical engineering plan. The larger product vision lives
in [vision.md](vision.md).

## v0 Goal

Ship a stable monitoring runtime with four reference modules:

- visual
- network
- finance/time-series
- infrastructure

v0 should prove the architecture, not the whole future product.

## v0 Definition of Done

- Core kernel starts cleanly.
- `PluginRegistry` discovers all four modules.
- FastAPI exposes health, modules, alerts, metrics, sessions, export, WebSocket,
  and dry-run command routes.
- All command execution is simulated and forced to `dry_run=true`.
- Sample data works out of the box.
- Tests, linting, typing, compile checks, and `git diff --check` pass.
- README accurately describes the current system and its limitations.
- `main` is tagged as a v0 release.

## Current Verification Commands

```bash
ruff check .
mypy core api modules
pytest tests -q
python -m compileall -q api core modules dashboard cli notifications tests scripts
git diff --check
```

On Windows systems with restricted temp directories:

```bash
set TEMP=%CD%\.tmp
set TMP=%CD%\.tmp
pytest tests -q --basetemp=.pytest_tmp
```

## v0 Safety Boundary

The command layer is dry-run only.

Allowed:

- propose a command
- persist it in SQLite
- approve it
- simulate execution
- emit `COMMAND_EXECUTED` or `COMMAND_FAILED`

Not allowed in v0:

- real PLC, Modbus, OPC-UA, MQTT, relay, robotics, or building-control adapters
- autonomous hardware actions
- marketing that implies production control readiness

## v1 Priorities

1. Docker Compose for API and dashboard.
2. GitHub Actions CI.
3. CLI with Typer.
4. Notification manager and console/Slack/Discord/email adapters.
5. Dashboard pages for all modules.
6. Prometheus-compatible metrics endpoint.
7. Contributor guide and module starter template.

## v2 Candidate Work

- policy engine for command approval
- append-only audit ledger
- authentication and role-based access control
- digital twin or scenario simulator
- distributed event bus adapter
- model registry and drift checks

## Non-Goals For Now

- building 100 modules before the kernel is boringly stable
- real actuation
- enterprise safety claims
- Kubernetes before Docker and CI are reliable
