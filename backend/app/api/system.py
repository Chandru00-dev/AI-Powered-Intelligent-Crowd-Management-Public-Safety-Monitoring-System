import time
import platform
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.database import get_db, engine
from backend.app.core.config import settings

router = APIRouter(prefix="/system", tags=["System"])

SERVER_START_TIME = time.time()

@router.get("/health")
def get_system_health(db: Session = Depends(get_db)):
    db_status = "UNKNOWN"
    db_dialect = engine.dialect.name
    try:
        db.execute(text("SELECT 1"))
        db_status = "CONNECTED"
    except Exception as e:
        db_status = f"DISCONNECTED: {str(e)}"

    uptime_seconds = int(time.time() - SERVER_START_TIME)

    return {
        "status": "HEALTHY" if db_status == "CONNECTED" else "DEGRADED",
        "app_name": settings.APP_NAME,
        "database_status": db_status,
        "database_type": db_dialect.upper(),
        "uptime_seconds": uptime_seconds,
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "phase": "PHASE 1 & PHASE 2 ACTIVE"
    }
