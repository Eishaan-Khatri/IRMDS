"""
Pydantic schemas for the FastAPI backend.

These schemas define the request and response shapes, ensuring that
all data moving across the network is strictly typed and serialized
properly.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────
# Generic & Paging
# ─────────────────────────────────────────────────────────


class PaginatedResponse(BaseModel):
    """Generic wrapper for list endpoints with pagination."""

    items: list[Any] = Field(description="The results for this page")
    total: int = Field(description="Total number of items matching the query")
    page: int = Field(description="Current page number (1-indexed)")
    limit: int = Field(description="Max items per page")


# ─────────────────────────────────────────────────────────
# Events & Alerts
# ─────────────────────────────────────────────────────────


class EventSchema(BaseModel):
    """Base schema for an event emitted by a module."""

    id: str
    timestamp: str
    module: str
    type: str
    severity: str
    data: dict[str, Any]


class AlertSchema(EventSchema):
    """An Event augmented with database/alert-manager specific fields."""

    escalated: bool = False
    session_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AlertStatsResponse(BaseModel):
    """Aggregated statistics for alerts."""

    severity_counts: dict[str, int]
    module_counts: dict[str, int]
    type_counts: dict[str, int]


# ─────────────────────────────────────────────────────────
# Modules
# ─────────────────────────────────────────────────────────


class ModuleSchema(BaseModel):
    """State and identity of an IRMDS module."""

    id: str
    display_name: str
    version: str
    status: str


class ModuleActionResponse(BaseModel):
    """Response after executing a module control action (start/stop)."""

    module_id: str
    action: str
    status: str
    success: bool
    message: str | None = None


# ─────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────


class ModuleMetricsSchema(BaseModel):
    """Latest real-time performance metrics for a specific module."""

    module_id: str
    metrics: dict[str, Any]


class SystemMetricsSchema(BaseModel):
    """Aggregated metrics across all currently running modules."""

    system_uptime_seconds: float
    modules: list[ModuleMetricsSchema]


# ─────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────


class SessionStartRequest(BaseModel):
    """Payload to start a custom monitoring session."""

    description: str | None = "Manual session"


class SessionSchema(BaseModel):
    """A bounded monitoring period with summary statistics."""

    id: str
    start_time: float
    end_time: float | None = None
    status: str
    summary: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────


class ModuleHealth(BaseModel):
    """Health breakdown for a specific module."""

    module_id: str
    healthy: bool
    status: str
    details: dict[str, Any]


class HealthResponse(BaseModel):
    """Overall system health report."""

    status: str = Field(description="'healthy' or 'degraded'")
    version: str
    uptime_seconds: float
    modules: list[ModuleHealth]
