"""
Alert history, filtering, and aggregation routes.
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session as DBSession

from api.dependencies import get_db_session
from api.schemas import AlertSchema, AlertStatsResponse, PaginatedResponse
from core.database import AlertRecord

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=PaginatedResponse)
def list_alerts(
    limit: int = 50,
    offset: int = 0,
    module: str | None = None,
    type: str | None = None,
    severity: str | None = None,
    session_id: str | None = None,
    db: DBSession = Depends(get_db_session)
):
    """Retrieve a paginated list of alerts with optional filters."""
    query = db.query(AlertRecord)

    if module:
        query = query.filter(AlertRecord.module == module)
    if type:
        query = query.filter(AlertRecord.type == type)
    if severity:
        query = query.filter(AlertRecord.severity == severity)
    if session_id:
        query = query.filter(AlertRecord.session_id == session_id)

    total = query.count()
    records = query.order_by(desc(AlertRecord.timestamp)).offset(offset).limit(limit).all()

    return PaginatedResponse(
        items=[AlertSchema.model_validate(r) for r in records],
        total=total,
        page=(offset // limit) + 1 if limit > 0 else 1,
        limit=limit
    )


@router.get("/latest", response_model=List[AlertSchema])
def get_latest_alerts(
    limit: int = Query(10, ge=1, le=100),
    db: DBSession = Depends(get_db_session)
):
    """Quickly grab the most recent alerts without pagination metadata."""
    records = db.query(AlertRecord).order_by(desc(AlertRecord.timestamp)).limit(limit).all()
    return [AlertSchema.model_validate(r) for r in records]


@router.get("/stats", response_model=AlertStatsResponse)
def get_alert_stats(
    db: DBSession = Depends(get_db_session)
):
    """Get aggregated alert statistics for the dashboard."""
    
    # Group by Severity
    severity_results = db.query(AlertRecord.severity, func.count(AlertRecord.id)).group_by(AlertRecord.severity).all()
    severity_counts = {sev: count for sev, count in severity_results}
    
    # Group by Module
    module_results = db.query(AlertRecord.module, func.count(AlertRecord.id)).group_by(AlertRecord.module).all()
    module_counts = {mod: count for mod, count in module_results}
    
    # Group by Type
    type_results = db.query(AlertRecord.type, func.count(AlertRecord.id)).group_by(AlertRecord.type).all()
    type_counts = {t: count for t, count in type_results}

    return AlertStatsResponse(
        severity_counts=severity_counts,
        module_counts=module_counts,
        type_counts=type_counts
    )


@router.get("/{alert_id}", response_model=AlertSchema)
def get_alert(
    alert_id: str,
    db: DBSession = Depends(get_db_session)
):
    """Get details for a specific alert by ID."""
    record = db.query(AlertRecord).filter(AlertRecord.id == alert_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    
    return AlertSchema.model_validate(record)
