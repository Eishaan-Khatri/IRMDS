<div align="center">

# IRMDS

**Intelligent Real-Time Monitoring & Decision System**

An open-source runtime for intelligent physical-space monitoring: one kernel,
four anomaly-detection modules, one event bus, one API, and a live dashboard.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20%2B%20WebSocket-009688?logo=fastapi&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-visual%20AI-111111)
![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-persistence-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

</div>

## What This Is

IRMDS is a modular monitoring platform for real-time anomaly detection across
very different signal types:

- visual surveillance
- synthetic network traffic
- financial time-series replay
- host infrastructure telemetry

Each domain module runs behind the same `BaseModule` contract, publishes
structured events to the same `EventBus`, and exposes metrics through the same
FastAPI backend. The current v0 focus is monitoring, alerting, observability,
and safe dry-run command simulation.

This repo should be read as the seed of a larger platform, not as a finished
industrial control system. Real hardware actuation is intentionally out of
scope for v0.

## Current Status

| Area | v0 State | Notes |
|:--|:--|:--|
| Kernel | Implemented | Sync/threaded module lifecycle, plugin discovery, event bus, metrics, config |
| API | Implemented | REST routes, WebSocket event streaming, request logging, app lifespan |
| Persistence | Implemented | SQLite-backed alerts, sessions, and dry-run command ledger |
| Visual module | Implemented | YOLO wrapper, tracker, zones, speed estimator, heatmap, pipeline |
| Network module | Implemented | Synthetic traffic generator, feature windows, anomaly detector, pipeline |
| Finance module | Implemented | OHLCV replay, features, Isolation Forest, CUSUM, anomaly events |
| Infrastructure module | Implemented | psutil collector, log analyzer, threshold events |
| Command layer | Simulated only | `/commands` proposes and approves dry-run commands; no hardware adapters |
| Dashboard | Early v0 | Streamlit command center, WebSocket feed, visual page and reusable charts |
| Tests | Green locally | 91 tests covering core, API, visual, finance, infrastructure, command flow, starter-module discovery |
| CI | Added after v0.1.0 | GitHub Actions runs compile, ruff, mypy, and pytest |
| Docker Compose | Added after v0.1.0 | Root Compose stack boots API + dashboard |
| CLI/demo | Added after v0.1.0 | `irmds demo` / `python scripts/demo.py` starts a sample-safe local demo |
| Notifications | Planned | Notification adapters remain future v1 work |

## Architecture

```text
                 data sources
        video | packets | OHLCV | system logs
                         |
                         v
              +----------------------+
              |    domain modules    |
              | visual network       |
              | finance infrastructure|
              +----------+-----------+
                         |
                         v
              +----------------------+
              |       EventBus       |
              | publish / subscribe  |
              | filtered history     |
              +----------+-----------+
                         |
          +--------------+---------------+
          |                              |
          v                              v
 +------------------+          +-------------------+
 |   AlertManager   |          | MetricsCollector  |
 | cooldown / dedup |          | latest + history  |
 | escalation       |          | rolling stats     |
 +--------+---------+          +---------+---------+
          |                              |
          +--------------+---------------+
                         |
                         v
              +----------------------+
              |      FastAPI API     |
              | REST + WebSocket     |
              +----------+-----------+
                         |
       +-----------------+------------------+
       |                                    |
       v                                    v
 Streamlit dashboard              exports / dry-run commands
```

## v0 Module Matrix

| Module ID | Domain | Main Inputs | Outputs |
|:--|:--|:--|:--|
| `visual` | Computer vision | webcam, video file, RTSP stream | `ZONE_ENTRY`, `ZONE_EXIT`, `LOITERING`, `CROWD_ALERT`, `SPEED_ANOMALY` |
| `network` | Traffic security | generated packet stream | `NET_METRICS`, `NET_ANOMALY` |
| `timeseries` | Finance replay | OHLCV CSV | `FIN_METRICS`, `FIN_ANOMALY` |
| `infrastructure` | Host monitoring | psutil metrics, syslog-style file | `INFRA_CPU_HIGH`, `INFRA_RAM_HIGH`, `INFRA_LOG_ANOMALY` |
| `actuation_gateway` | Simulated command execution | approved dry-run commands | `COMMAND_EXECUTED`, `COMMAND_FAILED` |

## Repository Layout

```text
IRMDS/
|-- .github/workflows/     GitHub Actions CI
|-- api/                  FastAPI app, dependencies, schemas, REST and WS routes
|-- docker/               Dockerfiles for API and dashboard
|-- core/                 kernel: modules, events, metrics, alerts, commands, DB
|-- dashboard/            Streamlit app, visual page, chart builders, WS client
|-- data/                 small deterministic sample data and zone config
|-- docs/                 project vision, v0/v1 plan, module guide, release notes
|-- models/               model provenance docs and ignored runtime weights
|-- modules/
|   |-- visual/           YOLO, tracking, speed, zones, heatmap, pipeline
|   |-- network/          packet generation, features, anomaly detection, pipeline
|   |-- timeseries/       finance replay, features, anomaly detection, pipeline
|   `-- infrastructure/   psutil collector, log analyzer, pipeline
|-- notifications/        notification package placeholder for v1
|-- scripts/              sample data generation and manual smoke checks
|-- tests/                unit and integration coverage
|-- CHANGELOG.md          release history
|-- compose.yml           root Docker Compose stack
|-- pyproject.toml        project metadata plus ruff, mypy, pytest config
|-- requirements.txt      runtime dependencies
`-- requirements-dev.txt  development and test dependencies
```

## Quick Start

### Quick Local Demo

This is the canonical lowest-friction proof that the runtime works. It starts
the API, starts sample-friendly modules, seeds one dry-run command, probes the
system, and exits. On a fresh checkout, complete the environment setup below
first.

```bash
python scripts/demo.py --smoke --no-dashboard
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

What the demo proves:

- plugin discovery finds `visual`, `network`, `timeseries`, and `infrastructure`
- the FastAPI backend starts and responds
- modules can be started through the API
- modules emit metrics/events through the shared runtime
- dry-run command proposal and approval work
- the simulated actuation gateway emits command events

### Installed CLI Demo

After installing the package in editable mode, the equivalent installed proof is:

```bash
python -m pip install -e .
irmds demo --smoke --no-dashboard
```

For an attached local demo with the dashboard:

```bash
python scripts/demo.py
```

Open:

```text
http://localhost:8000/docs
http://localhost:8501
```

The attached demo regenerates deterministic sample data, starts the API,
starts the dashboard unless `--no-dashboard` is passed, starts sample-friendly
modules, and seeds one dry-run command so the command ledger has visible
activity.

The visual module is opt-in because it may need a webcam/video file and YOLO
weights:

```bash
python scripts/demo.py --with-visual
```

### 1. Create an environment

```bash
git clone https://github.com/Eishaan-Khatri/IRMDS.git
cd IRMDS
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt -r requirements-dev.txt
```

macOS/Linux activation:

```bash
source .venv/bin/activate
```

### 2. Configure defaults

```bash
copy .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Important defaults:

| Variable | Default | Purpose |
|:--|:--|:--|
| `IRMDS_DATABASE_URL` | `sqlite:///data/irmds.db` | local persistence |
| `IRMDS_API_HOST` | `0.0.0.0` | API bind host |
| `IRMDS_API_PORT` | `8000` | API port |
| `IRMDS_CORS_ORIGINS` | `*` | dashboard/API CORS |
| `IRMDS_VISUAL_SOURCE` | `0` | webcam index or video path |
| `IRMDS_VISUAL_MODEL_PATH` | `models/yolov8n.pt` | YOLO weight location |
| `IRMDS_FINANCE_DATA_PATH` | `data/sample_stock.csv` | finance replay CSV |
| `IRMDS_INFRA_LOG_PATH` | `data/sample_syslog.log` | log analyzer input |

### 3. Generate sample data

The repo includes small deterministic samples. Regenerate them when needed:

```bash
python scripts/generate_sample_data.py
```

### 4. Run tests

```bash
ruff check .
mypy core api modules
pytest tests -q
```

On Windows systems with restricted temp folders, use a repo-local temp base:

```bash
set TEMP=%CD%\.tmp
set TMP=%CD%\.tmp
pytest tests -q --basetemp=.pytest_tmp
```

### 5. Start the API

```bash
uvicorn api.main:irmds_api --host 0.0.0.0 --port 8000 --reload
```

Compatibility alias:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

```text
http://localhost:8000/docs
```

### 6. Start the dashboard

```bash
streamlit run dashboard/app.py
```

Open:

```text
http://localhost:8501
```

## Docker Compose

From the repository root:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000/docs
http://localhost:8501
```

Stop the stack:

```bash
docker compose down
```

The Compose stack is intentionally sample-safe. It starts the API and
dashboard, mounts `data/` and `logs/`, and does not require a camera, YOLO
weights, or real hardware.

Docker uses `requirements-docker.txt`, which excludes `ultralytics`/PyTorch so
the demo images stay practical to build. Install `requirements.txt` on the host
when you need full visual inference.

## Full Visual YOLO Setup

The Docker demo does not install the full YOLO stack. For visual inference,
use the host environment:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Then configure:

```bash
IRMDS_VISUAL_SOURCE=0
IRMDS_VISUAL_MODEL_PATH=models/yolov8n.pt
```

Notes:

- `IRMDS_VISUAL_SOURCE=0` uses the default webcam.
- A video file path can be used instead of `0`.
- RTSP URLs are supported through OpenCV, but should be tested with real camera
  hardware before being claimed as production-ready.
- YOLO weights are ignored by git. Put local weights under `models/`.

## Dry-Run Command Safety Boundary

The command layer is deliberately simulation-only in v0.

- `dry_run` defaults to `true`
- `CommandBus` forces commands back to `dry_run=true` before persistence
- `ActuationGateway` never talks to hardware
- approved commands only produce simulated state transitions and events
- real actuation is deferred until policy checks, authentication, audit logs,
  simulation tests, and hardware safety interlocks exist

This keeps the project honest: IRMDS v0 proves the runtime and monitoring loop,
not physical control.

## Verification

Use the dedicated verification guide for exact checks and expected output:

- [docs/verification.md](docs/verification.md)

## GitHub Actions CI

The repository includes `.github/workflows/ci.yml`.

CI runs:

```bash
python -m compileall -q api core modules dashboard cli notifications tests scripts
ruff check .
mypy core api modules
pytest tests -q --basetemp=.pytest_tmp
```

The CI environment is configured to avoid webcam/model dependencies and to use
a temporary SQLite database.

## Building A Module

New modules should inherit `BaseModule`, publish structured events, and push
metrics through `MetricsCollector`.

Start here:

- [Module Starter Guide](docs/module_starter.md)

The important rule: the kernel should not need special-case code for a new
domain. If adding Module 5 requires changing every API route, the module
boundary is wrong.

## API Surface

| Method | Path | Description |
|:--|:--|:--|
| `GET` | `/` | system identity and uptime |
| `GET` | `/health` | overall health plus module health |
| `GET` | `/config` | sanitized runtime config |
| `GET` | `/modules` | discovered modules and statuses |
| `POST` | `/modules/{id}/start` | start a module |
| `POST` | `/modules/{id}/stop` | stop a module |
| `POST` | `/modules/{id}/restart` | restart a module |
| `GET` | `/alerts` | paginated/filterable alert history |
| `GET` | `/alerts/latest` | latest alerts |
| `GET` | `/alerts/stats` | alert counts by severity/module/type/time |
| `GET` | `/metrics` | latest metrics for all modules |
| `GET` | `/metrics/{module_id}` | latest metrics for one module |
| `GET` | `/sessions` | session history |
| `POST` | `/sessions/start` | start a monitoring session |
| `POST` | `/sessions/stop` | stop the active session |
| `GET` | `/export/alerts?format=csv` | export alerts as CSV |
| `GET` | `/export/alerts?format=json` | export alerts as JSON |
| `POST` | `/commands` | propose a dry-run command |
| `GET` | `/commands` | list recent dry-run commands |
| `GET` | `/commands/{id}` | inspect command state |
| `POST` | `/commands/{id}/approve` | approve simulated execution |
| `WS` | `/ws/events` | real-time event stream |

Example event:

```json
{
  "id": "evt_a3f8c2d1",
  "timestamp": "2026-05-04T10:15:32.456000+00:00",
  "module": "network",
  "type": "NET_ANOMALY",
  "severity": "CRITICAL",
  "data": {
    "anomaly_type": "DDOS_SUSPECT",
    "packets_per_second": 15000
  }
}
```

Example dry-run command:

```json
{
  "action": "SET_MAINTENANCE_MODE",
  "target_device": "SIM_DEVICE_01",
  "payload": {
    "reason": "operator test"
  },
  "dry_run": true
}
```

## Testing Evidence

Current v0 verification:

```text
ruff check .                 -> passed
mypy core api modules        -> passed
pytest tests -q              -> 91 passed
compileall                   -> passed
git diff --check             -> passed
```

CI now runs the same core checks on GitHub Actions for new pushes and pull
requests.

Coverage includes:

- config defaults and environment overrides
- event publish/subscribe/filter/history/unsubscribe
- alert cooldown, deduplication, escalation, persistence callback path
- visual tracker, zone manager, speed estimator, and visual pipeline
- API startup, REST routes, WebSocket event streaming
- module discovery for visual/network/timeseries/infrastructure
- finance replay through `PluginRegistry`
- infrastructure pipeline with mocked `psutil`
- dry-run command propose, fetch, approve, simulated completion, event emission

## What v0 Proves

IRMDS v0 proves the core platform shape:

```text
new module -> BaseModule -> EventBus -> AlertManager/Metrics -> API -> dashboard
```

That is the important architectural bet. The modules are reference
implementations that show the kernel can carry different domains without
special-casing the API.

## Known Limitations

- Visual inference depends on local camera/video/model availability.
- Network traffic is synthetic in v0, not live packet capture.
- Finance replay uses deterministic CSV samples, not exchange feeds.
- Infrastructure monitoring is local host-focused.
- Dashboard is functional but still early.
- Docker and CI are present, but should still be verified on a clean machine
  before calling the next release fully reproducible.
- Notification adapters are planned but not complete.
- No real hardware actuation exists or should be inferred from the command API.

## v1 Direction

The next useful release should harden reproducibility and first-run experience:

1. verify the new Docker stack from a fresh clone
2. record a short demo video
3. expand the CLI beyond `demo`
4. notification manager with console, Slack, Discord, email adapters
5. dashboard pages for all four modules
6. Prometheus-compatible metrics endpoint
7. contributor guide and richer module starter template
8. release automation for tags and changelog checks

## Long-Term Vision

The long-term idea is a runtime for intelligent physical spaces: small kernel,
strict module contract, typed events, observable behavior, safe simulation, and
eventual policy-gated command execution.

The near-term discipline is to keep v0 narrow and real. Make the monitoring
runtime reliable first; only then grow toward control-plane features.

See:

- [docs/vision.md](docs/vision.md)
- [docs/plan.md](docs/plan.md)
- [docs/gstack_README.md](docs/gstack_README.md)

## License

IRMDS is released under the MIT License. See [LICENSE](LICENSE).
