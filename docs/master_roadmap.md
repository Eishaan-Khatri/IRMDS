# IRMDS Master Roadmap: The 520-Week Manifest

## Year 1: The Sovereign Kernel

### Week 1: The Core Handshake (Performance & Memory)
**Objective:** Optimize the central nervous system (EventBus) for zero-copy efficiency.

**Engineering Tasks:**
- **Pre-allocated Event Pool:** Refactor `EventBus.publish` to use a `collections.deque` based object pool. This minimizes Python Garbage Collection (GC) pressure during high-frequency telemetry bursts (e.g., 1000+ packets/sec in the Network module).
- **Fast-Path Communication:** Implement a `bypass_serialization` flag for module-to-module communication. When a consumer and producer are in the same process, we pass the raw `Event` object instead of converting to/from JSON, saving ~15ms per dispatch.
- **Lock Contention Reduction:** Replace the global `threading.Lock` in the `MetricsCollector` with a `defaultdict` of per-module locks, allowing concurrent metric updates across different domain pipelines.

**Success Metric:** System latency reduced by 12% under 5k events/sec load.
