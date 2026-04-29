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
