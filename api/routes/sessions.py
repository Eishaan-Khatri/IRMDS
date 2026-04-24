"""
Sessions API routes (start, stop, list).
"""

import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session as DBSession

from api.dependencies import get_db_session
from api.schemas import PaginatedResponse, SessionSchema, SessionStartRequest
from core.database import SessionRecord

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("", response_model=PaginatedResponse)
def list_sessions(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    db: DBSession = Depends(get_db_session)
):
    """List monitoring sessions, ordered by newest first."""
    query = db.query(SessionRecord)
    
    if status is not None:
        query = query.filter(SessionRecord.status == status)

    total = query.count()
    records = query.order_by(desc(SessionRecord.start_time)).offset(offset).limit(limit).all()

    return PaginatedResponse(
        items=[SessionSchema.model_validate(r) for r in records],
        total=total,
        page=(offset // limit) + 1 if limit > 0 else 1,
        limit=limit
    )


@router.post("/start", response_model=SessionSchema)
def start_session(
    request: SessionStartRequest,
    db: DBSession = Depends(get_db_session)
):
    """Start a new monitoring session.
    
    Only one session can be active at a time. If an active session exists,
    it must be stopped first.
    """
    active = db.query(SessionRecord).filter(SessionRecord.status == "active").first()
    if active:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start session. Session '{active.id}' is currently active."
        )

    new_session = SessionRecord(
        id=f"sess_{uuid4().hex[:8]}",
        start_time=time.time(),
        status="active",
        summary={"description": request.description}
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return SessionSchema.model_validate(new_session)


@router.post("/stop", response_model=SessionSchema)
def stop_session(
    db: DBSession = Depends(get_db_session)
):
    """Stop the currently active session and compute basic summary."""
    active = db.query(SessionRecord).filter(SessionRecord.status == "active").first()
    if not active:
        raise HTTPException(
            status_code=400,
            detail="No active session found to stop."
        )

    end_time = time.time()
    active.end_time = end_time
    active.status = "completed"
    
    # Update the summary with duration
    s = dict(active.summary)
    s["duration_seconds"] = end_time - active.start_time
    active.summary = s

    # TODO: We could query the AlertRecord table here to summarize alerts
    # that occurred during this session window and attach to the summary.

    db.add(active)
    db.commit()
    db.refresh(active)

    return SessionSchema.model_validate(active)


@router.get("/{session_id}", response_model=SessionSchema)
def get_session(
    session_id: str,
    db: DBSession = Depends(get_db_session)
):
    """Get details of a specific session."""
    record = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    
    return SessionSchema.model_validate(record)
