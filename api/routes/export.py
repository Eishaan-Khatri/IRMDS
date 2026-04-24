"""
Data export routes (CSV/JSON dumps).
"""

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session as DBSession

from api.dependencies import get_db_session
from core.database import AlertRecord

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/alerts")
def export_alerts(
    format: str = "csv",
    limit: int = 1000,
    db: DBSession = Depends(get_db_session)
):
    """Export the most recent alerts in CSV or JSON format."""
    
    if format not in ("csv", "json"):
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'json'")
    
    records = db.query(AlertRecord).order_by(desc(AlertRecord.timestamp)).limit(limit).all()
    
    if format == "json":
        data = []
        for r in records:
            data.append({
                "id": r.id,
                "timestamp": r.timestamp,
                "module": r.module,
                "type": r.type,
                "severity": r.severity,
                "escalated": r.escalated,
                "session_id": r.session_id,
                "data": r.data
            })
            
        json_output = json.dumps(data, indent=2)
        return PlainTextResponse(
            content=json_output,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=irmds_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"}
        )
        
    elif format == "csv":
        # Create an in-memory string buffer for the CSV data
        output = io.StringIO()
        fieldnames = ["id", "timestamp", "module", "type", "severity", "escalated", "session_id", "data_json"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for r in records:
            writer.writerow({
                "id": r.id,
                "timestamp": r.timestamp,
                "module": r.module,
                "type": r.type,
                "severity": r.severity,
                "escalated": str(r.escalated),
                "session_id": r.session_id or "",
                "data_json": json.dumps(r.data)
            })
            
        # Reset pointer to start so FastAPI can read from it
        output.seek(0)
        
        # Iteration generator for StreamingResponse
        def iter_csv():
            yield from output

        return StreamingResponse(
            iter_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=irmds_alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
