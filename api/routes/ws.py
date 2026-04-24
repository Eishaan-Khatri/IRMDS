"""
WebSocket routing for real-time event streaming.
"""

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from api.dependencies import get_event_bus
from core.event_bus import Event, EventBus

router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/events")
async def websocket_events(
    websocket: WebSocket,
    modules: str | None = Query(None, description="Comma-separated list of modules to filter by"),
    types: str | None = Query(None, description="Comma-separated list of event types to filter by"),
    min_severity: str | None = Query(None, description="Minimum severity level (INFO, WARNING, CRITICAL)"),
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

    # Parse filters
    filter_modules = [m.strip() for m in modules.split(",")] if modules else None
    filter_types = [t.strip() for t in types.split(",")] if types else None

    # Async queue to pipe events from the sync EventBus callback
    # to the async websocket sender loop.
    queue: asyncio.Queue[Event] = asyncio.Queue()

    # Capture the active ASGI event loop so the thread can push into it
    loop = asyncio.get_running_loop()

    def sync_event_callback(event: Event):
        """Callback invoked by the core EventBus thread."""
        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except RuntimeError:
            pass # Loop is closed

    # Subscribe to EventBus with requested filters
    sub_id = event_bus.subscribe(
        callback=sync_event_callback,
        filter_module=filter_modules,
        filter_type=filter_types,
        filter_severity=min_severity
    )

    try:
        # Loop forever waiting for events in the queue to forward
        while True:
            event = await queue.get()
            payload: Dict[str, Any] = {
                "id": event.id,
                "timestamp": event.timestamp,
                "module": event.module,
                "type": event.type,
                "severity": event.severity.value,
                "data": event.data
            }
            await websocket.send_json(payload)
            
    except WebSocketDisconnect:
        # Client disconnected normally
        pass
    finally:
        # ALWAYS unsubscribe to prevent memory leaks in the EventBus
        event_bus.unsubscribe(sub_id)
