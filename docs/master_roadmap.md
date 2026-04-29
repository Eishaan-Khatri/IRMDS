# IRMDS Master Roadmap: The 520-Week Manifest

## Year 1: The Sovereign Kernel

### Week 1: The Core Handshake (Performance & Memory)
**Objective:** Optimize the central nervous system (EventBus) for zero-copy efficiency.

**Engineering Tasks:**
- **Pre-allocated Event Pool:** Refactor `EventBus.publish` to use a `collections.deque` based object pool. This minimizes Python Garbage Collection (GC) pressure during high-frequency telemetry bursts (e.g., 1000+ packets/sec in the Network module).
- **Fast-Path Communication:** Implement a `bypass_serialization` flag for module-to-module communication. When a consumer and producer are in the same process, we pass the raw `Event` object instead of converting to/from JSON, saving ~15ms per dispatch.
- **Lock Contention Reduction:** Replace the global `threading.Lock` in the `MetricsCollector` with a `defaultdict` of per-module locks, allowing concurrent metric updates across different domain pipelines.

**Success Metric:** System latency reduced by 12% under 5k events/sec load.

### Week 2: Adaptive Buffer Management (Flow Control)
**Objective:** Implement dynamic ring buffers for visual and network stream stability.

**Engineering Tasks:**
- **Auto-scaling Frame Buffers:** Refactor `modules/visual/frame_source.py` to use a dynamic queue depth. The buffer will monitor `VisualDetector` latency; if processing exceeds 50ms/frame, the buffer depth increases to prevent frame-drop, up to a configured memory limit.
- **Intelligent Frame Dropping:** Implement a "Skip Strategy" for the `VisualPipeline`. If the system detects a processing backlog, it will prioritize "Motion Frames" (where pixel deltas are high) and drop static frames to maintain real-time sync with the physical world.
- **Network Backpressure:** Add a `high_water_mark` to the `NetworkTrafficGenerator` queue. If the `FeatureExtractor` is overwhelmed, the generator will pause or sample packets (1-in-10) to maintain architectural stability without crashing the host memory.

**Success Metric:** 0% buffer overflows during a 30-second "DDoS burst" simulation.

### Week 3: Multi-Layer Thresholding (Alert Quality)
**Objective:** Implement "Consensus Alerts" in the AlertManager to eliminate false positive fatigue.

**Engineering Tasks:**
- **Cross-Module Correlator:** Update `core/alert_manager.py` to support "Multi-Signal Triggers." For example, a `NET_ANOMALY` from the network module will only fire a `CRITICAL` alert if the `INFRA` module simultaneously reports a CPU spike or the `VISUAL` module detects a person in the "Server Room" zone.
- **Damping & Debouncing:** Implement an exponential backoff for repeat alerts. If the same `LOITERING` event triggers 5 times, the manager will increase the cooldown from 10s to 60s, preventing "alert storms" from flooding the dashboard.
- **Dynamic Thresholding:** Add logic to the `AlertManager` to load per-hour sensitivity profiles. Decrease sensitivity during "Business Hours" (high expected activity) and increase it during "Dark Hours" (zero-tolerance for movement).

**Success Metric:** 40% reduction in "Noise" alerts (non-actionable INFO/WARNING).

### Week 4: The Metrics Registry (Self-Documentation)
**Objective:** Standardize telemetry schemas to allow auto-generation of dashboards and documentation.

**Engineering Tasks:**
- **Metric Registration API:** Update `core/metrics_collector.py` to require a `register_schema` call from each module. This defines the unit (e.g., "ms", "percentage", "bytes"), range (0-100), and labels for each metric key.
- **OpenMetrics Export:** Implement a Prometheus-compatible endpoint at `/metrics/prometheus` that iterates over the `MetricsCollector` registry and exports data in the standard text format.
- **Auto-Generated Data Dictionary:** Build a CLI command `irmds docs metrics` that parses the registry and generates a markdown table of every system metric, its source, and its meaning for end-users.

**Success Metric:** 100% of internal metrics are accessible via Prometheus/Grafana without manual mapping.
