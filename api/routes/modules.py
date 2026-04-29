"""
Module control API routes (start, stop, list).
"""

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_registry
from api.schemas import ModuleActionResponse, ModuleSchema
from core.plugin_registry import PluginRegistry

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.get("", response_model=list[ModuleSchema])
def list_modules(registry: PluginRegistry = Depends(get_registry)):
    """List all registered modules and their current statuses."""
    result = []
    for mod_dict in registry.list_modules():
        result.append(
            ModuleSchema(
                id=mod_dict["module_id"],
                display_name=mod_dict["display_name"],
                version=mod_dict["version"],
                status=mod_dict["status"],
            )
        )
    return result


@router.post("/{module_id}/start", response_model=ModuleActionResponse)
def start_module(module_id: str, registry: PluginRegistry = Depends(get_registry)):
    """Start a specific module by its ID."""
    try:
        mod = registry.get_module(module_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_id}' not found.",
        ) from exc

    try:
        registry.start_module(module_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ModuleActionResponse(
        module_id=module_id,
        action="start",
        status=mod.status.value,
        success=True,
        message=f"Module '{module_id}' started successfully.",
    )


@router.post("/{module_id}/stop", response_model=ModuleActionResponse)
def stop_module(module_id: str, registry: PluginRegistry = Depends(get_registry)):
    """Stop a specific module by its ID."""
    try:
        mod = registry.get_module(module_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_id}' not found.",
        ) from exc

    try:
        registry.stop_module(module_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ModuleActionResponse(
        module_id=module_id,
        action="stop",
        status=mod.status.value,
        success=True,
        message=f"Module '{module_id}' stopped successfully.",
    )


@router.post("/{module_id}/restart", response_model=ModuleActionResponse)
def restart_module(module_id: str, registry: PluginRegistry = Depends(get_registry)):
    """Restart a specific module (stop, then start)."""
    try:
        mod = registry.get_module(module_id)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_id}' not found.",
        ) from exc

    try:
        registry.restart_module(module_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ModuleActionResponse(
        module_id=module_id,
        action="restart",
        status=mod.status.value,
        success=True,
        message=f"Module '{module_id}' restarted successfully.",
    )
