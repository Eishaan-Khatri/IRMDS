"""
Custom exception hierarchy for IRMDS.

Every exception in the system inherits from `IRMDSError`, making it trivial
to catch all IRMDS-specific errors at the API boundary while letting
unexpected system errors propagate normally.

Hierarchy:
    IRMDSError
    ├── ConfigError
    │   └── ConfigValidationError
    ├── ModuleError
    │   ├── ModuleNotFoundError
    │   ├── ModuleAlreadyRunningError
    │   └── ModuleStartupError
    ├── AlertError
    ├── NotificationError
    └── DatabaseError
"""


class IRMDSError(Exception):
    """Base exception for all IRMDS errors.

    All custom exceptions inherit from this, allowing API error handlers
    to distinguish between expected application errors and unexpected
    system failures.
    """

    def __init__(self, message: str = "", *, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ─────────────────────────────────────────────────
# Configuration Errors
# ─────────────────────────────────────────────────


class ConfigError(IRMDSError):
    """Raised when configuration loading or parsing fails."""


class ConfigValidationError(ConfigError):
    """Raised when a config value is present but invalid.

    Example: IRMDS_VISUAL_CONFIDENCE=1.5 (must be 0.0–1.0)
    """


# ─────────────────────────────────────────────────
# Module Lifecycle Errors
# ─────────────────────────────────────────────────


class ModuleError(IRMDSError):
    """Base error for module lifecycle issues."""

    def __init__(self, module_id: str, message: str = "", **kwargs):
        self.module_id = module_id
        super().__init__(f"[{module_id}] {message}", **kwargs)


class ModuleNotFoundError(ModuleError):
    """Raised when a requested module ID doesn't exist in the registry."""

    def __init__(self, module_id: str):
        super().__init__(module_id, f"Module '{module_id}' is not registered.")


class ModuleAlreadyRunningError(ModuleError):
    """Raised when attempting to start a module that's already active."""

    def __init__(self, module_id: str):
        super().__init__(module_id, f"Module '{module_id}' is already running.")


class ModuleStartupError(ModuleError):
    """Raised when a module fails during its start() phase.

    Wraps the original exception so the API can return a meaningful
    error response without exposing internal stack traces.
    """

    def __init__(self, module_id: str, cause: Exception):
        self.cause = cause
        super().__init__(
            module_id,
            f"Module '{module_id}' failed to start: {cause}",
            details={"original_error": str(cause)},
        )


# ─────────────────────────────────────────────────
# Alert & Notification Errors
# ─────────────────────────────────────────────────


class AlertError(IRMDSError):
    """Raised when alert processing fails (storage, dedup, routing)."""


class NotificationError(IRMDSError):
    """Raised when a notification channel fails to deliver.

    Non-fatal by design — a failed Slack webhook should never crash
    the monitoring pipeline. The alert manager logs this and moves on.
    """

    def __init__(self, channel: str, message: str = ""):
        self.channel = channel
        super().__init__(f"[{channel}] {message}")


# ─────────────────────────────────────────────────
# Database Errors
# ─────────────────────────────────────────────────


class DatabaseError(IRMDSError):
    """Raised when a database operation fails.

    Wraps SQLAlchemy errors to keep the ORM layer from leaking
    into business logic.
    """
