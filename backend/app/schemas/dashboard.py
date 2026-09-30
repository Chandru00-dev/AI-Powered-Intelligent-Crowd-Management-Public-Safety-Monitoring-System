from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from backend.app.schemas.camera import CameraResponse

class DashboardAlertItem(BaseModel):
    id: int
    camera_name: str
    alert_type: str
    severity: str
    message: str
    timestamp: str
    status: str

class DashboardZoneItem(BaseModel):
    zone_id: str
    name: str
    people_count: int
    capacity: int
    occupancy_ratio: float
    density_level: str

class DashboardSummaryResponse(BaseModel):
    total_cameras: int
    online_cameras: int
    offline_cameras: int
    current_people: int
    peak_crowd: int
    active_alerts: int
    critical_alerts: int
    today_events: int
    system_status: str
    database_type: str
    recent_cameras: List[CameraResponse] = []
    recent_alerts: List[DashboardAlertItem] = []
    crowd_chart_labels: List[str] = []
    crowd_chart_data: List[int] = []
    zones: List[DashboardZoneItem] = []
    congestion_level: str = "NORMAL"

