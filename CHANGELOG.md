# Changelog

All notable IRMDS changes are documented here.

The project follows pragmatic semantic versioning while it is pre-1.0:

- `0.x` releases may still change internal contracts.
- Release notes call out safety boundaries explicitly.
- Every release should list verification commands that passed locally or in CI.

## v0.1.0 - 2026-05-04

First stabilized v0 release of IRMDS: an open-source runtime for intelligent
physical-space monitoring.

### Added

- Stabilized sync/threaded kernel contract.
- Integrated four module domains: visual, network, finance/timeseries, and
  infrastructure.
- Added dry-run command infrastructure with simulated actuation only.
- Added FastAPI command routes.
- Added deterministic sample data and sample-data generator.
- Added cleaned README, roadmap, and project positioning docs.

### Changed

- Set project and module metadata to `0.1.0`.
- Clarified current positioning as monitoring/runtime infrastructure rather
  than real autonomous control.
- Merged the phase-5 expansion work through a stabilized integration branch.

### Safety

- Real hardware actuation is not supported.
- Command execution is dry-run/simulated only.
- The command API should not be described as a production control system.

### Verified

- `python -m compileall -q api core modules dashboard cli notifications tests scripts`
- `ruff check .`
- `mypy core api modules`
- `pytest tests -q`
- `git diff --check`

## Unreleased

### Added

- GitHub Actions CI workflow for compile, lint, type-check, and tests.
- Dockerfiles and root Compose stack for API + dashboard.
- One-command sample demo via `python scripts/demo.py` and `irmds demo`.
- Module starter guide for contributors.
- Repo-local release notes source under `docs/releases/`.
