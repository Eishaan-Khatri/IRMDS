# IRMDS API Contract

This document describes the current v0 API contract. It is not frozen as a v1
public API yet, but new changes should preserve these shapes unless the change
is documented.

## Base URL

Local demo:

```text
http://127.0.0.1:8000
```

Docker Compose:

```text
http://localhost:8000
```

## Response Style

Most endpoints return JSON objects. Some legacy endpoints return raw lists.
v1 should normalize these, but v0 clients should expect the current shapes.

Errors use FastAPI's default shape:

```json
{
  "detail": "Human-readable error"
}
```

Validation errors use FastAPI/Pydantic validation details:

```json
{
  "detail": [
    {
      "loc": ["body", "field"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

## System

### `GET /`

Returns basic API identity.

```json
{
  "name": "IRMDS API",
  "status": "online",
  "description": "Intelligent Real-Time Monitoring & Decision System"
}
```

### `GET /health`

Returns API health and per-module health.

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 12.34,
  "modules": [
    {
      "module_id": "network",
      "healthy": false,
      "status": "stopped",
      "details": {}
    }
  ]
}
```

`healthy=false` for a stopped module does not mean the API is broken. Overall
status is degraded only when an active module reports unhealthy.

### `GET /config`

Returns sanitized runtime config. Secrets are masked.

## Modules

### `GET /modules`

Returns discovered modules.

```json
[
  {
    "id": "network",
    "display_name": "Network Security Analytics",
    "version": "0.1.0",
    "status": "stopped"
  }
]
```

### `POST /modules/{module_id}/start`

Starts a module.

### `POST /modules/{module_id}/stop`

Stops a module.

### `POST /modules/{module_id}/restart`

Stops and starts a module.

Common errors:

- `404`: module ID is not registered
- `400`: lifecycle operation failed

## Metrics

### `GET /metrics`

Returns uptime and latest metrics for running modules.

```json
{
  "system_uptime_seconds": 12.34,
  "modules": [
    {
      "module_id": "network",
      "metrics": {
        "pps": 800,
        "bps": 120000
      }
    }
  ]
}
```

Stopped modules are omitted from the `modules` list.

### `GET /metrics/{module_id}`

Returns latest metrics for one module. If the module exists but has no metrics
yet, `metrics` may be empty or null depending on the route path.

## Alerts

### `GET /alerts`

Returns paginated persisted alerts.

Query parameters:

- `limit`
- `offset`
- `module`
- `type`
- `severity`
- `since`
- `until`
- `session_id`

Shape:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "limit": 50
}
```

### `GET /alerts/latest`

Returns a raw list of recent alerts.

### `GET /alerts/stats`

Returns aggregate alert counts.

## Commands

The command API is simulation-only in v0.

### `POST /commands`

Proposes a dry-run command.

Request:

```json
{
  "action": "SET_MAINTENANCE_MODE",
  "target_device": "demo_line_01",
  "payload": {
    "reason": "operator test"
  },
  "dry_run": true
}
```

Response:

```json
{
  "status": "accepted",
  "command": {
    "id": "cmd_abc123",
    "action": "SET_MAINTENANCE_MODE",
    "target_device": "demo_line_01",
    "payload": {
      "reason": "operator test"
    },
    "state": "pending",
    "dry_run": true,
    "created_at": 1770000000.0,
    "updated_at": 1770000000.0,
    "error_reason": null
  }
}
```

`dry_run` is always forced to `true`.

### `POST /commands/{command_id}/approve`

Approves a pending command for simulated execution. The simulated gateway
transitions it through:

```text
pending -> approved -> executing -> completed
```

### `GET /commands`

Returns recent command ledger entries.

### `GET /commands/{command_id}`

Returns one command or `404`.

## WebSocket

### `WS /ws/events`

Streams real-time events from `EventBus`.

Common event shape:

```json
{
  "id": "evt_a3f8c2d1b4e5",
  "timestamp": "2026-05-07T08:00:00+00:00",
  "module": "network",
  "type": "NET_ANOMALY",
  "severity": "CRITICAL",
  "data": {
    "anomaly_type": "DDOS_SUSPECT"
  }
}
```

## v1 Contract Gaps

Before v1, the API should standardize:

- error shape
- list versus object response style
- API auth
- schema version fields
- pagination on all list endpoints
- documented status codes per endpoint
