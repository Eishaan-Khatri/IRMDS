"""
Command API routes.

These endpoints expose the simulated command ledger. v0/v1 commands are
always dry-run requests; approving one lets the simulated ActuationGateway
complete it and emit an EventBus notification.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from core.command_bus import Command, CommandState

router = APIRouter(prefix="/commands", tags=["Commands"])


def _get_command_bus(request: Request):
    return request.app.state.command_bus


@router.post("")
def propose_command(command: Command, request: Request) -> dict[str, Any]:
    """Propose a dry-run actuation command."""
    command_bus = _get_command_bus(request)
    proposed = command_bus.propose(command)
    return {"status": "accepted", "command": proposed.model_dump(mode="json")}


@router.get("")
def list_commands(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Return the recent command ledger."""
    command_bus = _get_command_bus(request)
    commands = command_bus.get_all_commands(limit=limit)
    return {"status": "success", "commands": [cmd.model_dump(mode="json") for cmd in commands]}


@router.get("/{command_id}")
def get_command_status(command_id: str, request: Request) -> dict[str, Any]:
    """Check a command's current state."""
    command_bus = _get_command_bus(request)
    command = command_bus.get_command(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")
    return {"status": "success", "command": command.model_dump(mode="json")}


@router.post("/{command_id}/approve")
def approve_command(command_id: str, request: Request) -> dict[str, Any]:
    """Approve a pending dry-run command for simulated execution."""
    command_bus = _get_command_bus(request)
    command = command_bus.transition_state(command_id, CommandState.APPROVED)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")
    if command.state == CommandState.FAILED:
        raise HTTPException(status_code=409, detail=command.error_reason)
    return {"status": "approved", "command": command.model_dump(mode="json")}
