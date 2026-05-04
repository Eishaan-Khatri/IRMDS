# IRMDS Module Starter Guide

IRMDS modules are small domain pipelines that plug into the core runtime.

The kernel does not need to know whether a module is looking at video frames,
network packets, stock ticks, or system telemetry. A module only needs to
implement the `BaseModule` contract, publish events, and push metrics.

## Module Contract

Every module should live under:

```text
modules/<module_id>/
|-- __init__.py
`-- pipeline.py
```

`pipeline.py` should expose a class that inherits from `core.base_module.BaseModule`.
The plugin registry discovers modules by scanning `modules/*/pipeline.py`.

Required metadata:

| Field | Purpose |
|:--|:--|
| `module_id` | Stable machine-readable ID, for example `network` |
| `display_name` | Human-readable name shown through the API |
| `version` | Module version string |
| `status` | Current lifecycle state |

Required methods:

| Method | Purpose |
|:--|:--|
| `start()` | Allocate resources and begin processing |
| `stop()` | Release resources and stop background work |
| `health_check()` | Return cheap health information |
| `get_metrics()` | Return current metrics for this module |

## Minimal Example

```python
import threading
import time

from core.base_module import BaseModule, ModuleStatus
from core.event_bus import Event, Severity


class ExamplePipeline(BaseModule):
    module_id = "example"
    display_name = "Example Module"
    version = "0.1.0"

    def __init__(self, event_bus, metrics_collector, config):
        super().__init__(event_bus, metrics_collector, config)
        self._running = threading.Event()
        self._thread = None

    def start(self) -> None:
        if self.status == ModuleStatus.RUNNING:
            return

        self.status = ModuleStatus.STARTING
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.status = ModuleStatus.RUNNING

    def stop(self) -> None:
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self.status = ModuleStatus.STOPPED

    def health_check(self) -> dict:
        return {
            "healthy": self.status == ModuleStatus.RUNNING,
            "status": self.status.value,
            "details": {"thread_alive": bool(self._thread and self._thread.is_alive())},
        }

    def get_metrics(self) -> dict:
        return self.metrics_collector.get_latest(self.module_id) or {}

    def _run(self) -> None:
        while self._running.is_set():
            self.metrics_collector.push(self.module_id, {"example_value": 1})
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="EXAMPLE_HEARTBEAT",
                    severity=Severity.INFO,
                    data={"message": "example module is alive"},
                )
            )
            time.sleep(1)
```

## Event Guidelines

Events should be compact, structured, and stable.

Use:

```json
{
  "module": "example",
  "type": "EXAMPLE_HEARTBEAT",
  "severity": "INFO",
  "data": {
    "message": "example module is alive"
  }
}
```

Prefer:

- stable event type names
- numeric metrics as numbers, not strings
- IDs for tracked objects/devices/entities
- short payloads that can be logged and rendered

Avoid:

- raw images or large binary payloads inside events
- secrets or credentials in event data
- blocking network calls inside the event publishing path

## Metrics Guidelines

Push the latest module metrics through `MetricsCollector`:

```python
self.metrics_collector.push(
    self.module_id,
    {
        "fps": 12.5,
        "latency_ms": 78.2,
        "active_tracks": 3,
    },
)
```

Metrics should be cheap to compute and safe to read often. The API and
dashboard may poll them frequently.

## Lifecycle Rules

For v0/v1, modules use a sync/threaded lifecycle:

- `start()` returns after background work is launched.
- `stop()` should be idempotent.
- `health_check()` must be cheap and should not run model inference.
- long-running work belongs in a background thread.
- exceptions inside worker threads should be logged and reflected in status.

This deliberately avoids mixing async module lifecycles with OpenCV, psutil,
and other blocking libraries.

## Local Verification

After adding a module, run:

```bash
python -m compileall -q api core modules dashboard cli notifications tests scripts
ruff check .
mypy core api modules
pytest tests -q
```

At minimum, add tests for:

- plugin discovery
- `start()` / `stop()`
- health check behavior
- emitted events
- pushed metrics

## Safety Boundary

Modules may detect, simulate, and recommend. They must not perform real hardware
actuation in v0/v1. Real control paths need policy checks, authentication,
authorization, audit logs, and hardware safety interlocks.
