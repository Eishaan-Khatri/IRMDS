"""
System-level API routes (health checks, config exports).
"""

import time

from fastapi import APIRouter, Depends, Request

from api.dependencies import get_app_config, get_registry
from api.schemas import HealthResponse, ModuleHealth
from core.config import IRMDSConfig
from core.plugin_registry import PluginRegistry

router = APIRouter()


@router.get("/", tags=["System"])
def get_system_info():
    """Get basic system identity and status."""
    return {
        "name": "IRMDS API",
        "status": "online",
        "description": "Intelligent Real-Time Monitoring & Decision System"
    }


@router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health(request: Request, registry: PluginRegistry = Depends(get_registry)):
    """Check the health of the entire system and all registered modules.
    
    A system is 'degraded' if any active module reports an unhealthy status.
    """
    uptime = time.time() - request.app.state.startup_time

    module_healths = []
    all_healthy = True

    for mod_info in registry.list_modules():
        mod_id = mod_info["module_id"]
        mod = registry.get_module(mod_id)
        if mod:
            h = mod.health_check()
            if mod.status.value == "running" and not h.get("healthy", False):
                all_healthy = False
            
            module_healths.append(
                ModuleHealth(
                    module_id=mod_id,
                    healthy=h.get("healthy", False),
                    status=h.get("status", "unknown"),
                    details=h.get("details", {})
                )
            )

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        version="1.0.0",
        uptime_seconds=uptime,
        modules=module_healths
    )


@router.get("/config", tags=["System"])
def get_sanitized_config(config: IRMDSConfig = Depends(get_app_config)):
    """Get the currently loaded configuration with secrets masked."""
    return config.get_sanitized()
