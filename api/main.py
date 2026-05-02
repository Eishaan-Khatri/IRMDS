"""
FastAPI application factory and main entry point.

This module initializes the IRMDS API, configures the application state,
and wires the the core background systems into the ASGI lifespan.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes import alerts, commands, export, metrics, modules, sessions, system, ws
from core.actuation_gateway import ActuationGateway
from core.alert_manager import AlertManager
from core.config import get_config
from core.command_bus import CommandBus
from core.database import init_db
from core.event_bus import EventBus
from core.logger import get_logger
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the IRMDS application.

    Startup:
        - Initialize the database.
        - Instantiate the core event/metrics bus.
        - Start the AlertManager to process event streams.
        - Register auto-discovered plugins/modules.
        - Attach these singletons to `app.state` for route dependencies.

    Shutdown:
        - Stop the AlertManager.
        - Stop all currently running modules to release local hardware (e.g. webcams).
    """
    startup_time = time.time()
    log.info("irmds_api_starting")

    # 1. Init Database
    init_db()

    # 2. Init Core Infrastructure
    config = get_config()
    event_bus = EventBus(max_history=config.alert_max_history)
    command_bus = CommandBus()
    metrics = MetricsCollector()

    # 3. Init and Start Alert Manager & Actuation Gateway
    alert_manager = AlertManager(event_bus, config)
    alert_manager.start()

    actuation_gateway = ActuationGateway(command_bus, event_bus)
    actuation_gateway.start()

    # 4. Plugin Discovery
    registry = PluginRegistry(event_bus, metrics, config)
    found_modules = registry.discover()
    log.info("plugin_discovery_complete", count=len(found_modules), modules=found_modules)

    # 5. Bind globally to app state so dependencies.py can inject them
    app.state.event_bus = event_bus
    app.state.command_bus = command_bus
    app.state.actuation_gateway = actuation_gateway
    app.state.metrics = metrics
    app.state.registry = registry
    app.state.alert_manager = alert_manager
    app.state.startup_time = startup_time

    log.info("irmds_api_ready", bind=f"{config.api_host}:{config.api_port}")

    yield  # Running block

    log.info("irmds_api_shutting_down")

    # 6. Clean Shutdown
    actuation_gateway.stop()
    alert_manager.stop()
    registry.stop_all()

    log.info("irmds_api_shutdown_complete")


def create_app() -> FastAPI:
    """Factory function to construct the FastAPI instance."""
    config = get_config()

    app = FastAPI(
        title="IRMDS API",
        description="Intelligent Real-Time Monitoring & Decision System",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    allowed_origins = [o.strip() for o in config.cors_origins.split(",") if o.strip()]
    if "*" in config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(process_time, 2),
        )
        return response

    # Register Routers
    app.include_router(system.router, tags=["System"])
    app.include_router(modules.router)
    app.include_router(commands.router)
    app.include_router(alerts.router)
    app.include_router(metrics.router)
    app.include_router(sessions.router)
    app.include_router(export.router)
    app.include_router(ws.router)

    return app


# Create the global app instance for Uvicorn
app = create_app()
