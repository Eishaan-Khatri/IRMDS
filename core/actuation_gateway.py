"""
Simulated actuation gateway.

This gateway never talks to real hardware. It polls approved dry-run commands,
marks them executing, waits briefly to emulate a device acknowledgement, then
marks them completed and emits an EventBus event.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from core.command_bus import Command, CommandBus, CommandState
from core.event_bus import Event, EventBus, Severity
from core.logger import get_logger


class ActuationGateway:
    """Dry-run command executor for v0/v1 demos and tests."""

    def __init__(
        self,
        command_bus: CommandBus,
        event_bus: EventBus,
        *,
        poll_interval: float = 0.1,
        execution_delay: float = 0.05,
    ):
        self.command_bus = command_bus
        self.event_bus = event_bus
        self.poll_interval = poll_interval
        self.execution_delay = execution_delay
        self.log = get_logger("actuation_gateway")
        self._running = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start polling approved commands."""
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._run,
            name="irmds-actuation-gateway",
            daemon=True,
        )
        self._thread.start()
        self.log.info("actuation_gateway_started", mode="dry_run")

    def stop(self) -> None:
        """Stop polling approved commands."""
        self._running.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self.log.info("actuation_gateway_stopped")

    def _run(self) -> None:
        """Poll for approved commands and simulate execution."""
        while self._running.is_set():
            try:
                for command in self.command_bus.get_commands_by_state(CommandState.APPROVED):
                    if not self._running.is_set():
                        break
                    self.execute_once(command)
            except Exception as exc:
                self.log.error("actuation_gateway_error", error=str(exc), exc_info=True)
            time.sleep(self.poll_interval)

    def execute_once(self, command: Command) -> Command | None:
        """Execute one approved command in dry-run mode."""
        if not command.dry_run:
            failed = self.command_bus.transition_state(
                command.id,
                CommandState.FAILED,
                reason="Real hardware actuation is disabled in v0/v1.",
            )
            self._publish_event("COMMAND_FAILED", failed or command)
            return failed

        executing = self.command_bus.transition_state(command.id, CommandState.EXECUTING)
        if executing is None or executing.state == CommandState.FAILED:
            return executing

        self.log.info(
            "simulating_command",
            command_id=executing.id,
            action=executing.action,
            target_device=executing.target_device,
        )
        time.sleep(self.execution_delay)

        completed = self.command_bus.transition_state(executing.id, CommandState.COMPLETED)
        if completed is not None:
            self._publish_event("COMMAND_EXECUTED", completed)
        return completed

    def _publish_event(self, event_type: str, command: Command) -> None:
        """Publish the command result to the EventBus."""
        payload: dict[str, Any] = {
            "command_id": command.id,
            "action": command.action,
            "target_device": command.target_device,
            "state": command.state.value,
            "dry_run": command.dry_run,
        }
        if command.error_reason:
            payload["error_reason"] = command.error_reason

        self.event_bus.publish(
            Event(
                module="actuation_gateway",
                type=event_type,
                severity=Severity.INFO if event_type == "COMMAND_EXECUTED" else Severity.WARNING,
                data=payload,
            )
        )
