"""
Dry-run command bus for simulated actuation.

Events describe what the system observed. Commands describe what the system
would like to do. In v0/v1, commands are persisted and executed only by the
simulated ActuationGateway. Real hardware adapters are deliberately out of
scope until policy, auth, audit, and safety interlocks exist.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.config import get_config
from core.logger import get_logger


class CommandState(StrEnum):
    """Allowed v0 command lifecycle states."""

    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class Command(BaseModel):
    """A simulated action request.

    `dry_run` is intentionally defaulted to True. CommandBus also enforces
    this value on persistence so API clients cannot accidentally request real
    actuation in v0/v1.
    """

    model_config = ConfigDict(use_enum_values=False)

    id: str = Field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:12]}")
    action: str = Field(min_length=1)
    target_device: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    state: CommandState = CommandState.PENDING
    dry_run: bool = True
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    error_reason: str | None = None


class CommandBus:
    """SQLite-backed command ledger for simulated actuation."""

    _VALID_TRANSITIONS: dict[CommandState, set[CommandState]] = {
        CommandState.PENDING: {CommandState.APPROVED, CommandState.FAILED},
        CommandState.APPROVED: {CommandState.EXECUTING, CommandState.FAILED},
        CommandState.EXECUTING: {CommandState.COMPLETED, CommandState.FAILED},
        CommandState.COMPLETED: set(),
        CommandState.FAILED: set(),
    }

    def __init__(self, db_path: Path | None = None):
        self.log = get_logger("command_bus")
        configured_url = get_config().database_url
        self.db_path = db_path or self._path_from_database_url(configured_url)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @staticmethod
    def _path_from_database_url(database_url: str) -> Path:
        """Resolve the SQLite path from the configured database URL."""
        if database_url.startswith("sqlite:///"):
            return Path(database_url.removeprefix("sqlite:///"))
        return Path("data/irmds.db")

    def _init_db(self) -> None:
        """Initialize the SQLite command ledger."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    target_device TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL,
                    dry_run INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    error_reason TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_commands_state ON commands(state)")

    @staticmethod
    def _to_row(command: Command) -> tuple[Any, ...]:
        return (
            command.id,
            command.action,
            command.target_device,
            json.dumps(command.payload),
            command.state.value,
            1 if command.dry_run else 0,
            command.created_at,
            command.updated_at,
            command.error_reason,
        )

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> Command:
        return Command(
            id=row[0],
            action=row[1],
            target_device=row[2],
            payload=json.loads(row[3]),
            state=CommandState(row[4]),
            dry_run=bool(row[5]),
            created_at=float(row[6]),
            updated_at=float(row[7]),
            error_reason=row[8],
        )

    def propose(self, command: Command) -> Command:
        """Persist a new command as pending and dry-run only."""
        command.state = CommandState.PENDING
        command.dry_run = True
        command.updated_at = time.time()

        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO commands (
                    id, action, target_device, payload, state,
                    dry_run, created_at, updated_at, error_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._to_row(command),
            )

        self.log.info(
            "command_proposed",
            command_id=command.id,
            action=command.action,
            target_device=command.target_device,
            dry_run=command.dry_run,
        )
        return command

    def get_command(self, command_id: str) -> Command | None:
        """Retrieve a command by ID."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM commands WHERE id = ?", (command_id,)).fetchone()
        return self._from_row(row) if row else None

    def get_commands_by_state(self, state: CommandState) -> list[Command]:
        """Return commands currently in one state."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT * FROM commands WHERE state = ?", (state.value,)).fetchall()
        return [self._from_row(row) for row in rows]

    def get_all_commands(self, limit: int = 50) -> list[Command]:
        """Return the most recent commands."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM commands ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def transition_state(
        self,
        command_id: str,
        new_state: CommandState,
        reason: str | None = None,
    ) -> Command | None:
        """Transition a command if the lifecycle allows it."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM commands WHERE id = ?", (command_id,)).fetchone()
            if row is None:
                return None

            command = self._from_row(row)
            if new_state not in self._VALID_TRANSITIONS[command.state]:
                command.state = CommandState.FAILED
                command.error_reason = (
                    reason
                    or f"Invalid transition from {command.state.value} to {new_state.value}"
                )
            else:
                command.state = new_state
                if reason:
                    command.error_reason = reason

            command.dry_run = True
            command.updated_at = time.time()
            conn.execute(
                """
                UPDATE commands
                SET state = ?, dry_run = ?, updated_at = ?, error_reason = ?
                WHERE id = ?
                """,
                (
                    command.state.value,
                    1 if command.dry_run else 0,
                    command.updated_at,
                    command.error_reason,
                    command.id,
                ),
            )

        self.log.info(
            "command_state_changed",
            command_id=command.id,
            new_state=command.state.value,
        )
        return command
