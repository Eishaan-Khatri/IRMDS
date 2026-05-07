# IRMDS Troubleshooting

Use this guide when setup, tests, demo mode, Docker, or dashboard behavior does
not match the README.

## First Diagnostic Commands

Run from the repo root:

```bash
python --version
python -m compileall -q api core modules dashboard cli notifications tests scripts examples
ruff check .
mypy core api modules
pytest tests -q
python scripts/demo.py --smoke --no-dashboard
docker compose config
```

If one fails, fix that layer before moving to the next one.

## Python Environment Issues

### `ModuleNotFoundError: No module named 'numpy'`

This usually means tests or commands were run with one Python environment, but
`python scripts/demo.py` is using a different interpreter.

From the repository root, use one of these fixes:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/demo.py --smoke --no-dashboard
```

Or bypass shell `PATH` ambiguity:

```powershell
.\.venv\Scripts\python.exe scripts\demo.py --smoke --no-dashboard
```

If the virtual environment does not exist yet:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### `python -m venv .venv` fails on Windows

Likely causes:

- Python installation is damaged.
- PowerShell is running from a restricted location.
- Temp directory permissions are broken.

Try:

```powershell
set TEMP=%CD%\.tmp
set TMP=%CD%\.tmp
python -m venv .venv
```

If `ensurepip` fails, repair or reinstall Python 3.12.

### Imports fail but dependencies are installed

Confirm the virtual environment is activated:

```bash
python -c "import sys; print(sys.executable)"
```

Then reinstall:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install -e .
```

## Test Issues

### Pytest permission errors in temp folders

Use a repo-local temp base:

```powershell
set TEMP=%CD%\.tmp
set TMP=%CD%\.tmp
pytest tests -q --basetemp=.tmp\pytest
```

If the error mentions `.pytest_tmp`, delete it after confirming it is inside the
repo:

```powershell
Remove-Item .pytest_tmp -Recurse -Force
```

### Tests fail because commands already exist

The test suite should use a test database:

```powershell
set IRMDS_DATABASE_URL=sqlite:///./.tmp/test_runtime/irmds_test.db
pytest tests -q
```

Do not run tests against `data/irmds.db`.

## Demo Issues

### Demo cannot bind to port 8000 or 8501

Another process is using the port.

Use alternate ports:

```bash
python scripts/demo.py --api-port 8780 --dashboard-port 8580
```

Or stop Docker Compose:

```bash
docker compose down
```

### Streamlit reports `server.port does not work when global.developmentMode is true`

The demo script passes `--global.developmentMode=false` when launching
Streamlit. If you run Streamlit manually, use:

```bash
streamlit run dashboard/app.py --global.developmentMode=false --server.port 8501
```

### Visual module fails to start

The visual module needs local camera/video/model setup. For demo mode, leave it
off:

```bash
python scripts/demo.py --smoke --no-dashboard
```

Only enable it when you have a camera/video source and YOLO weights:

```bash
python scripts/demo.py --with-visual
```

## Docker Issues

### `docker compose up` cannot reach Docker daemon

Start Docker Desktop first, then verify:

```bash
docker version
```

### Port already allocated

Check running containers:

```bash
docker ps
```

Stop stale stacks:

```bash
docker compose down
```

If a fresh-clone stack is running elsewhere, run `docker compose down` from that
folder too.

### Docker build is slow

The Docker demo uses `requirements-docker.txt`, which avoids the full
YOLO/PyTorch dependency chain. It still installs data and dashboard packages
such as Streamlit, pandas, scipy, and pyarrow, so the first build can take
several minutes.

## Dashboard Issues

### Dashboard opens but looks empty

Docker starts API and dashboard but does not automatically start modules.

Run the attached demo for visible activity:

```bash
python scripts/demo.py
```

Or start modules through the API:

```text
POST http://localhost:8000/modules/network/start
POST http://localhost:8000/modules/timeseries/start
POST http://localhost:8000/modules/infrastructure/start
```

### Dashboard cannot connect to API

Set `IRMDS_API_URL`:

```bash
IRMDS_API_URL=http://127.0.0.1:8000 streamlit run dashboard/app.py
```

PowerShell:

```powershell
$env:IRMDS_API_URL = "http://127.0.0.1:8000"
streamlit run dashboard/app.py
```

## Safety Issues

IRMDS v0/v1 commands are dry-run only. If you see code attempting to connect to
real actuators, PLCs, relays, robots, or physical machinery, treat it as a
blocker and do not merge it.
