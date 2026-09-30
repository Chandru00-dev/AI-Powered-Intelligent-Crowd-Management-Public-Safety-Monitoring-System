import json
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.setting import SystemSetting
from backend.app.models.user import User
from backend.app.services.auth_service import get_current_user, require_admin
from backend.app.schemas.setting import ThresholdSettings

router = APIRouter(prefix="/settings", tags=["Settings"])

DEFAULT_THRESHOLDS = {
    "crowd_warning_threshold": "30",
    "crowd_critical_threshold": "50",
    "high_density_threshold": "0.75",
    "congestion_movement_threshold": "0.5",
    "congestion_duration_seconds": "15",
    "fire_confidence_threshold": "0.65",
    "smoke_confidence_threshold": "0.60",
    "suspicious_object_confidence": "0.70",
    "abandoned_object_duration_seconds": "60",
}

@router.get("")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    settings_db = db.query(SystemSetting).all()
    result = {k: v for k, v in DEFAULT_THRESHOLDS.items()}
    for s in settings_db:
        result[s.key] = s.value
    return result

@router.put("")
def update_settings(
    thresholds: ThresholdSettings,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
) -> Dict[str, Any]:
    data = thresholds.model_dump()
    for key, val in data.items():
        val_str = str(val)
        setting_record = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting_record:
            setting_record.value = val_str
        else:
            db.add(SystemSetting(key=key, value=val_str, category="SAFETY_THRESHOLDS"))
    db.commit()
    return {"message": "Settings updated successfully.", "settings": data}
