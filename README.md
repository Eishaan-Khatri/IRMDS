# IRMDS - Intelligent Real-Time Monitoring & Decision System

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Visual_AI-111111)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue)

IRMDS is a modular real-time anomaly detection platform for visual surveillance,
network traffic, financial time-series, and infrastructure telemetry. It is built
as a production-style AI systems project: domain modules publish structured
events into a shared event bus, alerts are deduplicated and escalated, metrics
stream to a FastAPI backend, and operators monitor the system through a live
dashboard.

The project is designed to demonstrate end-to-end engineering range: computer
vision, streaming feature extraction, anomaly detection, backend APIs,
WebSockets, observability, testing, containerization, and deployable project
structure.

## Project Status

This repository is in active development toward the complete v1 architecture.
The visual module and core scaffolding are in place; the next stabilization
milestone is making the current API startup and network module contract fully
green under tests.

| Area | Status | Notes |
|:--|:--|:--|
| Core framework | Implemented | Config, event bus, metrics, plugin registry, sessions, exceptions |
| Visual module | Implemented | YOLO wrapper, tracker, zones, speed, heatmap, pipeline tests |
| FastAPI backend | Partially implemented | Routes exist; startup stabilization is next |
| Streamlit dashboard | Early implementation | Overview and visual page exist; needs polish and API config cleanup |
| Network module | In progress | Generator, extractor, detector exist; pipeline needs BaseModule alignment |
| Finance module | Planned | Time-series data source, feature extractor, detector, pipeline |
| Infrastructure module | Planned | psutil collector, log analyzer, anomaly detector, pipeline |
| Notifications and CLI | Planned | Slack, Discord, email, console, Typer CLI |
| Docker and CI | Planned | Container builds, GitHub Actions, coverage |

## Architecture

```text
                  +----------------------+
                  |      Data Sources    |
                  | video | packets | OHLCV | system |
                  +----------+-----------+
                             |
                             v
                +------------+-------------+
                |      Domain Modules      |
                | visual | network | finance | infra |
                +------------+-------------+
                             |
                             v
                    +--------+--------+
                    |    Event Bus    |
                    | pub/sub + history |
                    +--------+--------+
                             |
          +------------------+------------------+
          |                                     |
          v                                     v
 +--------+---------+                 +---------+--------+
 |  Alert Manager   |                 | Metrics Collector |
 | cooldown/dedup   |                 | latest + rolling  |
 | escalation       |                 | module metrics    |
 +--------+---------+                 +---------+--------+
          |                                     |
          +------------------+------------------+
                             |
                             v
                    +--------+--------+
                    |   FastAPI API   |
                    | REST + WebSocket |
                    +--------+--------+
                             |
                 +-----------+-----------+
                 |                       |
                 v                       v
          Streamlit Dashboard      Notifications / Export
```

## Modules

| Module | Purpose | Signals | Detection Strategy | Events |
|:--|:--|:--|:--|:--|
| Visual | People and zone monitoring | Detections, tracks, dwell time, speed | YOLOv8, IoU tracking, rule logic | `ZONE_ENTRY`, `LOITERING`, `CROWD_ALERT`, `SPEED_ANOMALY` |
| Network | Traffic anomaly detection | PPS, BPS, unique IPs, ports, entropy | Isolation Forest, EMA z-score, hard rules | `NET_METRICS`, `NET_ANOMALY`, `NET_BASELINE_SET` |
| Finance | Market anomaly detection | OHLCV, returns, volatility, RSI, volume | Isolation Forest, CUSUM, flash-crash rules | `FIN_METRICS`, `FIN_FLASH_CRASH`, `FIN_VOLATILITY_SPIKE` |
| Infrastructure | Host and log monitoring | CPU, RAM, disk, network I/O, process stats, logs | psutil thresholds, Isolation Forest, error-rate spikes | `INFRA_CPU_HIGH`, `INFRA_RAM_HIGH`, `INFRA_LOG_ERROR_SPIKE` |

## Current Repository Layout

```text
IRMDS/
|-- api/                  FastAPI app, routes, schemas, dependencies
|-- core/                 Base module contract, event bus, metrics, config
|-- dashboard/            Streamlit app, visual page, chart and websocket helpers
|-- data/                 Runtime/sample data such as zone configuration
|-- models/               Model documentation and runtime weight location
|-- modules/
|   |-- visual/           Visual detection pipeline
|   |-- network/          Traffic generator, feature extraction, detector
|   |-- timeseries/       Finance module package placeholder
|   `-- infrastructure/   Infrastructure module package placeholder
|-- notifications/        Notification package placeholder
|-- tests/                Unit and integration tests
|-- pyproject.toml        Project metadata and tool configuration
|-- requirements.txt      Runtime dependencies
`-- requirements-dev.txt  Test and development dependencies
```

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Eishaan-Khatri/IRMDS.git
cd IRMDS
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Configure

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Key configuration values:

| Variable | Default | Description |
|:--|:--|:--|
| `IRMDS_VISUAL_SOURCE` | `0` | Webcam index, video path, or stream URL |
| `IRMDS_VISUAL_MODEL_PATH` | `models/yolov8n.pt` | YOLOv8 model path |
| `IRMDS_DATABASE_URL` | `sqlite:///data/irmds.db` | SQLite database URL |
| `IRMDS_API_HOST` | `0.0.0.0` | API bind host |
| `IRMDS_API_PORT` | `8000` | API port |
| `IRMDS_CORS_ORIGINS` | `*` | Allowed dashboard origins |

### 3. Run tests

```bash
pytest tests -v
```

Focused visual pipeline checks:

```bash
pytest tests/unit/test_tracker.py tests/unit/test_speed_estimator.py tests/unit/test_zone_manager.py tests/integration/test_visual_pipeline.py -v
```

### 4. Run the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs are available at:

```text
http://localhost:8000/docs
```

### 5. Run the dashboard

```bash
streamlit run dashboard/app.py
```

Dashboard URL:

```text
http://localhost:8501
```

## API Overview

| Method | Path | Description |
|:--|:--|:--|
| `GET` | `/` | System identity and status |
| `GET` | `/health` | Overall and per-module health |
| `GET` | `/config` | Sanitized runtime configuration |
| `GET` | `/modules` | Registered modules and lifecycle status |
| `POST` | `/modules/{id}/start` | Start a module |
| `POST` | `/modules/{id}/stop` | Stop a module |
| `POST` | `/modules/{id}/restart` | Restart a module |
| `GET` | `/alerts` | Paginated alert history |
| `GET` | `/alerts/latest` | Latest alerts |
| `GET` | `/alerts/stats` | Alert aggregations |
| `GET` | `/metrics` | Metrics for all running modules |
| `GET` | `/metrics/{module_id}` | Metrics for one module |
| `GET` | `/sessions` | Monitoring session history |
| `POST` | `/sessions/start` | Start a monitoring session |
| `POST` | `/sessions/stop` | Stop the active session |
| `GET` | `/export/alerts?format=csv` | Export alerts as CSV |
| `GET` | `/export/alerts?format=json` | Export alerts as JSON |
| `WS` | `/ws/events` | Real-time event stream |

Example event payload:

```json
{
  "id": "evt_a3f8c2d1",
  "timestamp": "2026-04-23T10:15:32.456000+00:00",
  "module": "visual",
  "type": "SPEED_ANOMALY",
  "severity": "CRITICAL",
  "data": {
    "object_id": 3,
    "speed_ms": 3.4,
    "classification": "RUNNING"
  }
}
```

## Visual Module

The visual pipeline is the most mature module in the current codebase. It turns
video frames into structured real-time events.

Processing flow:

```text
FrameSource -> YOLOv8 Detector -> IoU Tracker -> Zone Manager
            -> Speed Estimator -> Heatmap -> Event Bus + Metrics
```

Implemented capabilities:

- Lazy YOLOv8 model loading
- Person detection filtering
- IoU-based persistent tracking IDs
- Polygon zone entry and exit events
- Loitering and crowd alerts
- Dynamic speed estimation using bounding-box height calibration
- Motion heatmap accumulation and export
- Headless background pipeline compatible with API control
- Unit and integration tests with mocked frame sources and detections

## Network Module

The network module is designed for synthetic traffic simulation and streaming
network anomaly detection.

Target flow:

```text
TrafficGenerator -> FeatureExtractor -> NetworkAnomalyDetector
                 -> Event Bus + Metrics
```

Designed detection coverage:

- DDoS-like packet bursts
- Port scanning behavior
- Data exfiltration-like byte spikes
- General traffic anomalies through Isolation Forest
- Short-term spikes through EMA z-score logic

## Finance Module

The finance module will replay or synthesize OHLCV data and detect market
anomalies in real time.

Planned features:

- CSV replay with configurable speed
- Synthetic random-walk generator with injected anomalies
- Log returns, rolling volatility, RSI, Bollinger position, momentum
- Flash crash rule detection
- CUSUM regime-change detection
- Isolation Forest anomaly scoring

## Infrastructure Module

The infrastructure module will monitor host health and log streams.

Planned features:

- CPU, RAM, disk, network I/O, process count
- Top CPU and RAM processes
- Log tailing and severity classification
- Error-rate spike detection
- Static critical thresholds and Isolation Forest anomaly scoring

## Notifications

IRMDS is designed to route processed alerts to multiple notification channels.

Target channels:

- Console notifier with Rich formatting
- Slack incoming webhook
- Discord webhook
- SMTP email

Notification routing will respect the configured minimum severity:

```bash
IRMDS_NOTIFY_ON_SEVERITY=CRITICAL
```

## CLI Target

The planned Typer CLI will provide a local control surface:

```bash
irmds start
irmds start --modules visual,network
irmds status
irmds alerts --follow
irmds config show
irmds benchmark --module visual --duration 30
irmds data generate --all
```

## Docker Target

The deployment target is a two-service Docker Compose stack:

```text
api        FastAPI service on port 8000
dashboard  Streamlit service on port 8501
```

Expected command once Docker files are implemented:

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Testing Strategy

| Layer | Purpose |
|:--|:--|
| Unit tests | Validate isolated core and module components |
| Integration tests | Validate pipeline behavior from input to emitted events |
| API tests | Validate REST and WebSocket behavior with FastAPI TestClient |
| E2E tests | Validate all modules through API, event bus, metrics, and dashboard |

Current test coverage includes:

- Event bus publish, subscribe, filtering, history, unsubscribe
- Alert cooldown, deduplication, escalation, callback routing
- Config defaults and environment overrides
- Tracker association and IoU behavior
- Speed estimator physics and classification
- Zone manager geometry, entry, exit, loitering, crowd alerts
- Visual pipeline integration with synthetic frames

## Roadmap

| Milestone | Goal |
|:--|:--|
| Stabilization | Fix API startup, network BaseModule contract, WebSocket filters, dashboard runtime bug |
| Network v1 | Complete network pipeline and tests |
| Finance v1 | Add OHLCV data source, features, detector, pipeline, tests |
| Infrastructure v1 | Add psutil collector, log analyzer, detector, pipeline, tests |
| Persistence | Persist processed alerts and session summaries consistently |
| Notifications | Add console, Slack, Discord, email routing |
| CLI | Add Typer commands for start, stop, status, alerts, config, benchmark |
| Dashboard v1 | Complete overview, visual, network, finance, infra, alerts pages |
| Deployment | Add Docker, GitHub Actions CI, coverage, release workflow |
| Portfolio polish | Add final README assets, screenshots, benchmark table, GitHub Pages showcase |

## Design Principles

- Modular first: adding a new domain should not require rewriting the API.
- Structured events: every module speaks the same event language.
- Real-time by default: metrics and alerts are meant to stream, not batch.
- Testable pipelines: live dependencies are mocked in CI-friendly tests.
- Operator clarity: alert cooldown, deduplication, and escalation are first-class.
- Honest production shape: configuration, logging, persistence, Docker, and CI are part of the design, not afterthoughts.

## Related Work

IRMDS is the production-oriented evolution of the visual anomaly detection work
in Edge-VCA:

- Edge-VCA: https://github.com/Eishaan-Khatri/Edge-VCA
- IRMDS: https://github.com/Eishaan-Khatri/IRMDS

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Author

Built by Eishaan Khatri as a portfolio-grade AI systems project spanning
computer vision, backend engineering, anomaly detection, infrastructure
monitoring, and real-time dashboards.
