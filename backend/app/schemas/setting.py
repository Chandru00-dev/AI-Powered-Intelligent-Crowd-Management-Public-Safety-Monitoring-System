from typing import Optional
from pydantic import BaseModel

class SettingItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    category: Optional[str] = "GENERAL"

class SettingUpdate(BaseModel):
    value: str

class ThresholdSettings(BaseModel):
    crowd_warning_threshold: int = 30
    crowd_critical_threshold: int = 50
    high_density_threshold: float = 0.75
    congestion_movement_threshold: float = 0.5
    congestion_duration_seconds: int = 15
    fire_confidence_threshold: float = 0.65
    smoke_confidence_threshold: float = 0.60
    suspicious_object_confidence: float = 0.70
    abandoned_object_duration_seconds: int = 60
