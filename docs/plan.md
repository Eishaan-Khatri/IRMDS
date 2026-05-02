## Plan: IRMDS — Total Factory Brain Implementation

TL;DR: Expand IRMDS from a monitoring kernel into a safe, auditable, simulation-first control plane. Prioritize kernel stability, a transactional `CommandBus` + simulated `ActuationGateway`, a Digital Twin test harness, and two high-value MVP control modules (Predictive Maintenance and Energy Orchestrator). Enforce safety by design: hardware fail-safes, policy gating, signed commands, and mandatory simulation passes in CI.

**Steps**
1. Discovery & scope (depends on 0): confirm safety boundary, legal constraints, and pilot hardware. Output: product spec and safety checklist.
2. Stabilize kernel (depends on 1): fix `modules/network/pipeline.py` to follow `BaseModule` lifecycle; add heartbeat/quarantine logic in `core/plugin_registry.py`. (Files: [core/base_module.py](core/base_module.py), [modules/network/pipeline.py](modules/network/pipeline.py), [core/plugin_registry.py](core/plugin_registry.py)).
3. Tests & CI (parallel with 2): add unit tests for lifecycle, integration tests for EventBus, and CI pipeline to run them. (Files: `tests/unit`, `tests/integration`, `pyproject.toml`).
4. CommandBus design (depends on 2,3): define JSON schema and state machine for commands (`PENDING→VALIDATED→APPROVED→EXECUTING→ACKED/FAILED`). Create REST endpoints `POST /commands`, `GET /commands/{id}` in `api/routes/modules.py` or new `api/routes/commands.py`.
5. CommandBus prototype (depends on 4): implement persistent queue (SQLite-backed for dev, Kafka adapter later), command ledger, and signing verification. Add `dry_run` flag support.
6. ActuationGateway design & simulate-first (parallel with 4/5): design adapters for OPC-UA, Modbus, MQTT; implement simulation driver that mimics device acks and failure modes. Keep hardware adapters behind explicit enable flags.
7. Policy Engine & Safety Supervisor (depends on 5,6): implement declarative policy checks and approval flows. Safety Supervisor enforces E-Stop and interlocks (software checks plus hardware interlock hooks). (Files: [api/main.py](api/main.py), new `core/policy.py`).
8. Digital Twin & Simulation (depends on 6,7): implement deterministic simulator for factory topology and device emulation; integrate with CI so every command/policy change runs scenario tests.
9. MVP modules (parallel after 2): implement `Predictive Maintenance` (FFT + threshold + ERP ticketing) and `Energy Orchestrator` (short-term load forecasting, scheduled load-shifting). Both must emit Events and propose Commands to CommandBus (require policy approval).
10. MLOps & data pipeline: instrument data capture, model registry, deterministic training pipelines, shadow deployments, and drift detection.
11. HIL & Pilot: deploy ActuationGateway to a hardened pilot edge host, run HIL tests with certified E-Stop and supervised actuation.
12. Productionization: scale to distributed backend (Kafka, Postgres), add K8s manifests, monitoring SLOs, runbooks, and compliance package.

**Relevant files**
- [core/base_module.py](core/base_module.py) — module contract and lifecycle
- [core/event_bus.py](core/event_bus.py) — immutable events and subscriptions
- [core/alert_manager.py](core/alert_manager.py) — dedup/escalation logic
- [core/plugin_registry.py](core/plugin_registry.py) — discovery & management
- [modules/network/pipeline.py](modules/network/pipeline.py) — current lifecycle mismatch (blocker)
- [modules/visual/pipeline.py](modules/visual/pipeline.py) — exemplar module
- [api/main.py](api/main.py) — app lifespan and DI
- [tests/integration/test_api_endpoints.py](tests/integration/test_api_endpoints.py) — integration tests

**Verification**
1. Unit tests: module lifecycle (`start/stop/health`), EventBus subscription/filtering, AlertManager cooldown/escalation.
2. Integration tests: API endpoints, WebSocket streaming, module start/stop through PluginRegistry.
3. Simulation tests: scenario scripts in Digital Twin covering normal operation, sensor dropouts, model drift, and actuator failures.
4. HIL: supervised relay/actuator tests with E-Stop engaged; all actuations produce signed, auditable logs.
5. Acceptance: pilot runs for 2 weeks with KPI thresholds (MTTR, false positive rate, successful automated actions).

**Decisions & assumptions**
- Default dev persistence: SQLite under `data/`; production uses PostgreSQL. (See [core/database.py](core/database.py)).
- In-process `EventBus` is acceptable for single-edge deployment; add Kafka/Redis adapters for cluster mode.
- Software never replaces certified hardware safety mechanisms — safety plane is hardware-first.

**Estimated timeline & effort (team of 3: architect, backend, ML/edge engineer)**
- Phase 0 (1 week): discovery, scope, safety checklist.
- Phase 1 (2 weeks): kernel stabilization, unit tests, CI baseline.
- Phase 2 (3 weeks): CommandBus + ActuationGateway (simulate-first) + policy engine skeleton.
- Phase 3 (4 weeks): Digital Twin v0 + CI simulation integration.
- Phase 4 (6–8 weeks): Predictive Maintenance + Energy Orchestrator MVPs + MLOps basics.
- Phase 5 (4 weeks): HIL tests, pilot deployment, docs and runbooks.
Total: ~4–5 months to a pilot-ready system with simulated actuators; additional months for full HIL and certification.

**Further considerations**
1. Start with a single pilot line and one non-critical actuator to prove the control loop. 2. Invest in simulation and signed audit trails early — they are the project's largest multiplier for safety and trust. 3. Plan for external safety certification: allocate budget/time for IEC/ISO compliance early.

**Short copy for README / stakeholder deck**
IRMDS will evolve into a simulation-first, policy-gated control plane: modules publish immutable Events; the `CommandBus` carries signed, auditable Commands; the `ActuationGateway` executes only after policy validation and simulation passes; hardware safety remains primary.


## Plan: Repo comprehension and short summary
(Analysis completed on 2026-04-27: concise evaluation saved in chat.)


TL;DR: IRMDS is a modular, production-oriented real-time monitoring and anomaly-detection platform. It uses a plugin-based architecture where domain modules (visual, network, timeseries, infra) run as background `BaseModule` workers, publish immutable `Event` objects to a central `EventBus`, and are processed by an `AlertManager` for deduplication/escalation before being exposed via a FastAPI backend and a Streamlit dashboard.

**Steps**
1. Explore and verify entry points: confirm how to start the FastAPI server and Streamlit dashboard (manual check on `api/main.py`, `dashboard/app.py`).
2. Inspect core subsystems to validate contracts: `BaseModule`, `EventBus`, `AlertManager`, `PluginRegistry`.
3. Review representative domain pipelines: `modules/visual/pipeline.py` and `modules/network/pipeline.py` for adherence to `BaseModule`.
4. Run unit/integration tests covering API, event bus, and alert manager to validate runtime assumptions.
5. Produce a short remediation list for any contract mismatches (e.g., network module async mismatch).

**Relevant files**
- [api/main.py](api/main.py) — FastAPI app & lifespan
- [dashboard/app.py](dashboard/app.py) — Streamlit UI entry point
- [core/base_module.py](core/base_module.py) — module lifecycle contract
- [core/event_bus.py](core/event_bus.py) — Event schema & pub/sub
- [core/alert_manager.py](core/alert_manager.py) — deduplication/escalation logic
- [core/plugin_registry.py](core/plugin_registry.py) — plugin discovery
- [modules/visual/pipeline.py](modules/visual/pipeline.py) — implemented domain pipeline
- [modules/network/pipeline.py](modules/network/pipeline.py) — network pipeline (potential mismatch)
- [tests/integration/test_api_endpoints.py](tests/integration/test_api_endpoints.py) — API/WebSocket integration tests

**Verification**
1. `pytest -q tests/unit tests/integration` — ensure core units pass
2. `uvicorn api.main:app --reload` then curl `/health` and `/modules`
3. `streamlit run dashboard/app.py` to validate WebSocket streaming and UI

**Decisions / Assumptions**
- Default DB is SQLite under `data/` unless `DATABASE_URL` env var is set.
- YOLO model weights and large artifacts are expected to be placed under `models/`.
- The plugin registry follows a strict `BaseModule` pattern; modules not following it will fail discovery or runtime control.

**Further considerations**
1. Confirm how CLI (`cli/`) should be invoked; CLI appears stubbed and may require wiring in `pyproject.toml` entry points.
2. Prioritize fixing `modules/network/pipeline.py` to inherit `BaseModule` if it needs to participate in registry lifecycle.
3. Verify Docker/CI expectations in repo docs before assuming production readiness.

**Short repo summary (for quick copy)**
IRMDS is a modular Real-Time Monitoring & Decision System: plugin-based domain modules run as background workers, publish immutable events to a central event bus, and flow through an AlertManager into a FastAPI API and Streamlit dashboard for real-time observability and alerts.
