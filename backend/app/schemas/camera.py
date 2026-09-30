from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.models.camera import CameraInputType, CameraStatus

class CameraBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    location: str = Field(..., min_length=2, max_length=200)
    input_type: CameraInputType
    source: str = Field(..., min_length=1, description="Path, device index or RTSP URL")
    username: Optional[str] = None
    description: Optional[str] = None

class CameraCreate(CameraBase):
    password: Optional[str] = None

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    input_type: Optional[CameraInputType] = None
    source: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None

class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    input_type: CameraInputType
    source: str
    username: Optional[str] = None
    has_password: bool = False
    status: CameraStatus
    enabled: bool
    resolution: Optional[str] = "N/A"
    fps: Optional[float] = 0.0
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CameraTestResponse(BaseModel):
    success: bool
    status: CameraStatus
    message: str
    details: Optional[Dict[str, Any]] = None
