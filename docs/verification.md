# IRMDS Verification Guide

This document is the current v0 verification checklist. It is intentionally
short and command-oriented so a new contributor can tell whether the repo is
healthy without reading the whole codebase.

## Verified Baseline

Latest verified main commit:

```text
f32c26e fix: slim docker demo dependencies
```

GitHub Actions status checked on 2026-05-07:

```text
workflow: CI
commit: f32c26e0f54c779689e6ba40bdf424087f4f4d7c
status: completed
conclusion: success
url: https://github.com/Eishaan-Khatri/IRMDS/actions/runs/25483507512
```

## Local Quality Gates

Run from the repository root:

```bash
python -m compileall -q api core modules dashboard cli notifications tests scripts
ruff check .
mypy core api modules
pytest tests -q
git diff --check
```

Expected result:

```text
compileall: no output
ruff: All checks passed!
mypy: Success: no issues found in 50 source files
pytest: 91 passed
git diff --check: no output
```

## Fresh Clone Verification

Run from outside the repo:

```powershell
cd D:\Projects
git clone https://github.com/Eishaan-Khatri/IRMDS.git IRMDS-fresh
cd IRMDS-fresh
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
mypy core api modules
pytest tests -q
```

Expected result:

```text
ruff: All checks passed!
mypy: Success: no issues found
pytest: all tests pass
```

## Canonical Demo Proofs

Lowest-friction repo-local proof:

```bash
python scripts/demo.py --smoke --no-dashboard
```

Installed CLI proof:

```bash
python -m pip install -e .
irmds demo --smoke --no-dashboard
```

Expected output shape:

```text
[demo] generating deterministic sample data
[demo] starting API: http://127.0.0.1:8000
[demo] discovered modules: infrastructure, network, timeseries, visual
[demo] started module: network
[demo] started module: timeseries
[demo] started module: infrastructure
[demo] proposed and approved dry-run command: cmd_<id>
[demo] dashboard data surfaces ready: modules, metrics, commands, alerts
[demo] API docs:      http://127.0.0.1:8000/docs
[demo] health:        http://127.0.0.1:8000/health
[demo] press Ctrl+C to stop
```

The exact command ID changes on every run. The module order may vary if Python
package discovery order changes, but the four module IDs should be present.

## Docker Verification

Docker Desktop must be running first.

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000/docs
http://localhost:8501
```

Expected result:

```text
api container: healthy
dashboard container: running
/health: HTTP 200
/docs: HTTP 200
dashboard: HTTP 200
```

Stop:

```bash
docker compose down
```

## Known Environment Notes

### Windows venv and pip permissions

On one Windows verification machine, creating a brand-new `.venv` in a fresh
clone was blocked by local Python/pip permission issues. The repo itself still
verified cleanly when run against an existing dependency bundle. If this happens:

1. Confirm Python 3.12 is installed and visible with `python --version`.
2. Run PowerShell as a normal user, not from a locked-down system directory.
3. Try a repo-local temp directory:

   ```powershell
   set TEMP=%CD%\.tmp
   set TMP=%CD%\.tmp
   python -m venv .venv
   ```

4. If `ensurepip` is blocked, repair or reinstall the local Python runtime.

### Docker Desktop requirement

The Compose stack requires Docker Desktop or another reachable Docker daemon.
If `docker version` cannot reach the server, start Docker Desktop before running
`docker compose up --build`.

### Full YOLO dependency versus Docker demo dependency

The host `requirements.txt` includes the full visual stack, including
`ultralytics`. The Docker demo intentionally installs `requirements-docker.txt`,
which excludes `ultralytics` and uses `opencv-python-headless` so the sample
stack builds without downloading the full PyTorch/YOLO dependency chain.

Use the host setup when you want full visual inference with local YOLO weights.
Use Docker when you want the sample-safe API and dashboard demo.
