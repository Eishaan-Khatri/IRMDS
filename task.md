# IRMDS — Task Checklist

> Living document. Mark [x] as you complete items, [/] for in-progress.

---

## Phase 1 — Project Scaffolding & Core Framework ✅

### Day 1: Project Setup ✅
- [x] Create full directory structure (all folders + __init__.py files)
- [x] Create pyproject.toml (project metadata, ruff config, mypy config, pytest config)
- [x] Create requirements.txt (production deps)
- [x] Create requirements-dev.txt (dev deps)
- [x] Create .gitignore (Python, IDE, .env, __pycache__, models/*.pt, data/*.db, logs/)
- [x] Create .env.example (all IRMDS_ prefixed env vars with defaults)
- [x] Create LICENSE (MIT)
- [x] Create .pre-commit-config.yaml (ruff, mypy, trailing whitespace)
- [x] Push initial scaffold to GitHub

### Day 2: Config, Logging, Exceptions ✅
- [x] core/config.py — Pydantic BaseSettings with all config fields
- [x] core/logger.py — Structured JSON logging via structlog
  - [x] Console output (colored, human-readable)
  - [x] File output (JSON lines to logs/irmds.log)
  - [x] Per-module context binding (module="visual" etc.)
  - [x] Test: log entries contain timestamp, level, module, event
- [x] core/exceptions.py — Custom exception hierarchy

### Day 3: Event Bus & Metrics Collector ✅
- [x] core/event_bus.py — In-process pub/sub
- [x] core/metrics_collector.py — Real-time metrics store
- [x] Thread-safe with threading.Lock

### Day 4: Base Module, Plugin Registry, Alert Manager, Session ✅
- [x] core/base_module.py — Abstract base class (Sync/Threaded)
- [x] core/plugin_registry.py — Module auto-discovery
- [x] core/alert_manager.py — Smart alert handling
  - [x] Cooldown, Deduplication, Escalation
  - [x] Persistence to SQLite
- [x] core/session.py — Session lifecycle
- [x] Database setup (SQLAlchemy models)

---

## Phase 2 — Visual Module (v0 Reference) ✅

### Day 5-8: Implementation ✅
- [x] modules/visual/detector.py (YOLOv8)
- [x] modules/visual/tracker.py (Centroid IoU)
- [x] modules/visual/speed_estimator.py
- [x] modules/visual/zone_manager.py
- [x] modules/visual/heatmap.py
- [x] modules/visual/frame_source.py
- [x] modules/visual/pipeline.py

### Day 9–10: Visual Module Tests ✅
- [x] tests/unit/test_tracker.py (11 tests)
- [x] tests/unit/test_speed_estimator.py (7 tests)
- [x] tests/unit/test_zone_manager.py (15 tests)
- [x] tests/integration/test_visual_pipeline.py (6 tests)

---

## Phase 3 — FastAPI Backend (v0 Reference) ✅

### Day 11-14: Implementation ✅
- [x] api/main.py (Lifespan, Middleware, Routers)
  - [x] Request logging middleware
- [x] api/schemas.py (Pydantic contracts)
- [x] api/routes/ (system, modules, alerts, metrics, sessions, export, ws)
- [x] WebSocket /ws/events with filtering

### Day 15: API Tests ✅
- [x] tests/integration/test_api_endpoints.py (87 total tests passed)

---

## Phase 4 — Network Module (v0 Stabilization) ✅

### Day 19-21: Implementation ✅
- [x] modules/network/schemas.py
- [x] modules/network/traffic_generator.py
- [x] modules/network/feature_extractor.py
- [x] modules/network/anomaly_detector.py (Isolation Forest + Z-Score)
- [x] modules/network/pipeline.py (Stabilized to BaseModule contract)

---

## Phase 5 — Sample Data & v1 Polish ✅

### Day 22: Sample Data Generator ✅
- [x] scripts/generate_sample_data.py
  - [x] Generate sample_stock.csv
  - [x] Generate sample_traffic.json (simulated via TrafficGenerator)
  - [x] Generate sample_syslog.log
  - [x] Generate zones_config.json
- [x] Push to GitHub

### Day 23-25: Missing Modules ✅
- [x] modules/timeseries/ (Finance)
- [x] modules/infrastructure/ (Infra)

---

## Phase 6-10 — Deployment & Scale

- [ ] CLI Tool (Typer)
- [ ] Notifications (Slack/Discord)
- [ ] Dashboard Polish (Streamlit)
- [ ] Docker & CI/CD
- [ ] Elite README & Docs site
