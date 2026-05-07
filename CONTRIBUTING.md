# Contributing To IRMDS

IRMDS is an open-source runtime for intelligent physical-space monitoring. The
current project phase is v0/v1: monitoring, alerts, metrics, dashboard, and
dry-run command simulation.

Real hardware actuation is intentionally out of scope until policy checks,
authentication, audit logs, simulation tests, and hardware safety interlocks
exist.

## Development Setup

```bash
git clone https://github.com/Eishaan-Khatri/IRMDS.git
cd IRMDS
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
```

Windows activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux activation:

```bash
source .venv/bin/activate
```

## Before You Change Code

Create a branch:

```bash
git checkout -b codex/short-description
```

Keep changes focused. If a task touches unrelated areas, split it into separate
branches.

## Verification Gates

Run these before opening a PR:

```bash
python -m compileall -q api core modules dashboard cli notifications tests scripts examples
ruff check .
mypy core api modules
pytest tests -q
git diff --check
```

For demo-impacting changes, also run:

```bash
python scripts/demo.py --smoke --no-dashboard
python -m cli.main demo --smoke --no-dashboard
docker compose config
```

If Docker behavior changed, run:

```bash
docker compose up --build
docker compose down
```

## Module Contributions

Read [docs/module_starter.md](docs/module_starter.md) first.

Module rules:

- Inherit from `BaseModule`.
- Use the sync/threaded lifecycle.
- Keep `health_check()` cheap.
- Publish small structured `Event` payloads.
- Push stable metric dictionaries.
- Add tests for discovery, start/stop, events, and metrics.
- Do not add real hardware actuation.

## Documentation Contributions

Docs should be specific and executable. Prefer:

- exact commands
- expected output
- known failure modes
- links to code paths

Avoid vague instructions like "run the app" without naming the command.

## Pull Request Checklist

Before opening a PR:

- [ ] Scope is focused.
- [ ] Tests pass locally.
- [ ] Docs were updated if behavior changed.
- [ ] Demo commands still work if touched.
- [ ] No generated caches or runtime databases are committed.
- [ ] No secrets are committed.
- [ ] Dry-run command safety boundary is preserved.

## Safety Rule

IRMDS v0/v1 is monitoring and simulation only. Any PR that introduces real
physical actuation must be rejected until the project has policy, auth, audit,
simulation, and hardware safety interlock layers.
