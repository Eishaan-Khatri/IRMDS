"""
Structured logging for IRMDS.

Uses `structlog` to produce machine-readable JSON logs with human-friendly
console output during development. Every log entry automatically includes:

    - timestamp (ISO 8601)
    - level (debug, info, warning, error, critical)
    - module (which component emitted the log)
    - event (what happened)
    - any additional key-value context

Why structlog over stdlib logging?
    1. Structured output — JSON logs are grep-able, parseable, indexable
    2. Context binding — attach module_id once, it appears in every log
    3. Processor pipeline — timestamps, formatting, and enrichment are composable
    4. Zero-config pretty printing for development, JSON for production

Usage:
    from core.logger import get_logger

    log = get_logger("visual")
    log.info("frame_processed", fps=24.5, latency_ms=40.8)
    # → {"timestamp": "2026-04-23T10:15:32", "level": "info",
    #    "module": "visual", "event": "frame_processed",
    #    "fps": 24.5, "latency_ms": 40.8}
"""

from __future__ import annotations

import logging
import sys
from typing import cast

import structlog


def setup_logging(*, json_output: bool = False, log_level: str = "INFO") -> None:
    """Configure the global structlog + stdlib logging pipeline.

    Call this once at application startup (in api/main.py or cli/main.py).
    Subsequent calls are safe but redundant.

    Args:
        json_output: If True, emit JSON lines (for production / Docker).
                     If False, emit colored, human-readable output (development).
        log_level:   Minimum log level to emit. One of: DEBUG, INFO, WARNING, ERROR.
    """
    # Shared processors applied to every log entry, regardless of output format.
    shared_processors: list[structlog.types.Processor] = [
        # Add log level string (info, warning, error, etc.)
        structlog.stdlib.add_log_level,
        # Add ISO 8601 timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Unpack exception info into the event dict
        structlog.processors.format_exc_info,
        # Clean up internal structlog keys
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: structlog.types.Processor
    if json_output:
        # Production: machine-readable JSON lines to stdout
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored, padded, human-friendly console output
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            pad_event=40,  # Align key-value pairs
        )

    structlog.configure(
        processors=[
            # Filter by log level before any processing (performance)
            structlog.stdlib.filter_by_level,
            *shared_processors,
            # Prepare for the final renderer
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the stdlib root logger to route through structlog's formatter.
    # This ensures that both structlog loggers AND third-party libraries
    # (uvicorn, sqlalchemy, etc.) produce consistent output.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("ultralytics").setLevel(logging.WARNING)


def get_logger(module: str) -> structlog.stdlib.BoundLogger:
    """Create a logger with pre-bound module context.

    Every log entry from this logger will automatically include
    `"module": "<module>"` in its output.

    Args:
        module: Identifier for the component (e.g., "visual", "api", "core").

    Returns:
        A structlog BoundLogger instance with the module context attached.

    Example:
        log = get_logger("network")
        log.info("baseline_trained", windows=60, model="IsolationForest")
    """
    return cast("structlog.stdlib.BoundLogger", structlog.get_logger(module=module))
