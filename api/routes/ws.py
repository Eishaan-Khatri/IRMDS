"""
WebSocket routing for real-time event streaming.
"""

import asyncio
from contextlib import suppress
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from core.event_bus import Event, Severity

router = APIRouter(prefix="/ws", tags=["WebSockets"])


def _parse_csv_filter(value: str | None) -> set[str] | None:
    """Parse a comma-separated query parameter into a set."""
    if not value:
        return None
    parsed = {item.strip() for item in value.split(",") if item.strip()}
    return parsed or None


def _parse_severity(value: str | None) -> Severity | None:
    """Parse a severity string into the enum used by EventBus."""
    if not value:
        return None
    try:
        return Severity[value.strip().upper()]
    except KeyError:
        return None


@router.websocket("/events")
async def websocket_events(
    websocket: WebSocket,
    modules: str | None = Query(None, description="Comma-separated list of modules to filter by"),
    types: str | None = Query(None, description="Comma-separated list of event types to filter by"),
    min_severity: str | None = Query(
        None, description="Minimum severity level (INFO, WARNING, CRITICAL)"
    ),
):
    """
    WebSocket endpoint for real-time streaming of system events.

    Clients can filter events by passing query parameters during connection:
    - `modules` (e.g., `?modules=visual,network`)
    - `types` (e.g., `?types=SPEED_ANOMALY,LOITERING`)
    - `min_severity` (e.g., `?min_severity=WARNING`)
    """
    await websocket.accept()

    event_bus = websocket.app.state.event_bus

    # Parse filters. EventBus supports one exact module/type filter, so the
    # WebSocket route handles multi-value module/type filters in the callback.
    filter_modules = _parse_csv_filter(modules)
    filter_types = _parse_csv_filter(types)
    filter_severity = _parse_severity(min_severity)

    # Async queue to pipe events from the sync EventBus callback
    # to the async websocket sender loop.
    queue: asyncio.Queue[Event] = asyncio.Queue()

    # Capture the active ASGI event loop so the thread can push into it
    loop = asyncio.get_running_loop()

    def sync_event_callback(event: Event):
        """Callback invoked by the core EventBus thread."""
        if filter_modules and event.module not in filter_modules:
            return
        if filter_types and event.type not in filter_types:
            return
        with suppress(RuntimeError):
            loop.call_soon_threadsafe(queue.put_nowait, event)

    # Subscribe to EventBus with requested filters
    sub_id = event_bus.subscribe(
        callback=sync_event_callback,
        filter_severity=filter_severity,
    )

    try:
        # Loop forever waiting for events in the queue to forward
        while True:
            event = await queue.get()
            payload: dict[str, Any] = {
                "id": event.id,
                "timestamp": event.timestamp,
                "module": event.module,
                "type": event.type,
                "severity": event.severity.value,
                "data": event.data,
            }
            await websocket.send_json(payload)

    except WebSocketDisconnect:
        # Client disconnected normally
        pass
    finally:
        # ALWAYS unsubscribe to prevent memory leaks in the EventBus
        event_bus.unsubscribe(sub_id)
