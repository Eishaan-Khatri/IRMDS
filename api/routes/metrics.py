"""
Metrics API routes (real-time performance stats).
"""

from fastapi import APIRouter, Depends, HTTPException, Request

from api.dependencies import get_metrics_collector, get_registry
from api.schemas import ModuleMetricsSchema, SystemMetricsSchema
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("", response_model=SystemMetricsSchema)
def get_all_metrics(
    request: Request,
    metrics: MetricsCollector = Depends(get_metrics_collector),
    registry: PluginRegistry = Depends(get_registry)
):
    """Retrieve current metrics for all running modules."""
    import time
    
    uptime = time.time() - request.app.state.startup_time
    module_metrics = []

    for mod_info in registry.list_modules():
        mod_id = mod_info["module_id"]
        # Only poll metrics for running modules
        mod = registry.get_module(mod_id)
        if mod and mod.status.value == "running":
            stats = metrics.get_latest(mod_id)
            if stats:
                module_metrics.append(
                    ModuleMetricsSchema(
                        module_id=mod_id,
                        metrics=stats
                    )
                )

    return SystemMetricsSchema(
        system_uptime_seconds=uptime,
        modules=module_metrics
    )


@router.get("/{module_id}", response_model=ModuleMetricsSchema)
def get_module_metrics(
    module_id: str,
    metrics: MetricsCollector = Depends(get_metrics_collector),
    registry: PluginRegistry = Depends(get_registry)
):
    """Retrieve current metrics for a specific module."""
    try:
        registry.get_module(module_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found.")
    
    stats = metrics.get_latest(module_id)
    return ModuleMetricsSchema(
        module_id=module_id,
        metrics=stats
    )
