# IRMDS Module Starter Guide

IRMDS modules are domain pipelines that plug into the core runtime. The kernel
does not need to know whether a module watches video, packets, stock ticks, logs,
or something else. A module only needs to satisfy the `BaseModule` contract,
publish structured events, and push metrics.

## Directory Contract

Every runtime-discoverable module should live under:

```text
modules/<module_id>/
|-- __init__.py
`-- pipeline.py
```

The plugin registry scans `modules/*/pipeline.py`, imports the file, and
registers classes that inherit from `core.base_module.BaseModule` and define a
non-empty `module_id`.

## BaseModule Lifecycle Contract

v0/v1 uses a synchronous, threaded lifecycle. Do not define async lifecycle
methods for modules unless the kernel contract changes.

Required class attributes:

| Field | Required | Purpose |
|:--|:--|:--|
| `module_id` | yes | Stable machine ID, for example `network` |
| `display_name` | yes | Human-readable label shown through the API |
| `version` | yes | Module version string |

Required methods:

| Method | Required | Rules |
|:--|:--|:--|
| `_run()` | yes | Main background loop. Runs after `BaseModule.start()` launches the thread. |
| `health_check()` | yes | Must be cheap. Do not run inference, packet capture, or slow I/O here. |
| `get_metrics()` | yes | Return current metrics for this module. Must be safe to call frequently. |

Inherited lifecycle methods:

| Method | Provided By | Behavior |
|:--|:--|:--|
| `start()` | `BaseModule` | Sets status to `STARTING`, launches `_safe_run()` in a daemon thread. |
| `stop()` | `BaseModule` | Clears `_running`, joins the worker thread, sets status to `STOPPED`. |
| `restart()` | `BaseModule` | Calls `stop()` then `start()`. |
| `to_dict()` | `BaseModule` | Serializes module state for API responses. |

Status values:

```text
stopped -> starting -> running -> stopping -> stopped
                         |
                         v
                       error
```

Implementation rules:

- Loop while `self._running.is_set()`.
- Release files, cameras, sockets, and model handles before `_run()` exits.
- Catch expected domain errors inside `_run()` when recovery is possible.
- Let unexpected errors raise so `BaseModule._safe_run()` can mark status as
  `ERROR`.
- Use `self.metrics.push(self.module_id, {...})` for metrics.
- Use `self.event_bus.publish(Event(...))` for events.

## Minimal Module

The repo includes a starter example in:

```text
examples/minimal_module/
```

Core shape:

```python
import time
from typing import Any

from core.base_module import BaseModule, ModuleStatus
from core.event_bus import Event, Severity


class MinimalPipeline(BaseModule):
    module_id = "minimal"
    display_name = "Minimal Example Module"
    version = "0.1.0"

    def _run(self) -> None:
        while self._running.is_set():
            self.metrics.push(self.module_id, {"heartbeat_count": 1})
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="MINIMAL_HEARTBEAT",
                    severity=Severity.INFO,
                    data={"message": "minimal module is alive"},
                )
            )
            time.sleep(1.0)

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": self.status == ModuleStatus.RUNNING,
            "status": self.status.value,
            "details": {"thread_alive": bool(self._thread and self._thread.is_alive())},
        }

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.get_latest(self.module_id) or {}
```

## Event Schema

Runtime events are immutable `core.event_bus.Event` objects.

Fields:

| Field | Type | Rule |
|:--|:--|:--|
| `id` | string | Auto-generated `evt_<id>` unless explicitly supplied. |
| `timestamp` | string | Auto-generated UTC ISO 8601 timestamp. |
| `module` | string | Source module ID. |
| `type` | string | Stable uppercase event type. |
| `severity` | enum | `INFO`, `WARNING`, or `CRITICAL`. |
| `data` | object | Small JSON-serializable payload. |

Example:

```json
{
  "id": "evt_a3f8c2d1b4e5",
  "timestamp": "2026-05-07T08:00:00+00:00",
  "module": "minimal",
  "type": "MINIMAL_HEARTBEAT",
  "severity": "INFO",
  "data": {
    "message": "minimal module is alive"
  }
}
```

Event rules:

- Use stable event type names.
- Put numeric values in `data` as numbers, not strings.
- Include IDs for tracked objects, devices, sessions, or entities when relevant.
- Do not put raw images, video frames, large blobs, secrets, or credentials in
  event payloads.
- Do not block the event publishing path with slow network calls.

## Metric Schema

Metrics are module-owned dictionaries pushed through `MetricsCollector`:

```python
self.metrics.push(
    self.module_id,
    {
        "fps": 12.5,
        "latency_ms": 78.2,
        "active_tracks": 3,
    },
)
```

Metric rules:

- Keep metric keys stable once exposed.
- Use snake_case names.
- Use numbers, booleans, strings, or small lists/dicts.
- Make metrics cheap to compute.
- Do not assume the dashboard is the only consumer; API clients may poll them.

## Plugin Discovery Test Pattern

At minimum, a new module should prove:

1. `PluginRegistry.discover()` can find it.
2. `start()` transitions it into `RUNNING`.
3. `stop()` returns it to `STOPPED`.
4. It emits at least one event.
5. It pushes at least one metric.

The repo contains a starter-style discovery test in:

```text
tests/unit/test_module_starter.py
```

## Local Verification

After adding a module, run:

```bash
python -m compileall -q api core modules dashboard cli notifications tests scripts
ruff check .
mypy core api modules
pytest tests -q
```

## Safety Boundary

Modules may detect, simulate, and recommend. They must not perform real hardware
actuation in v0/v1. Real control paths need policy checks, authentication,
authorization, audit logs, simulation tests, and hardware safety interlocks.
