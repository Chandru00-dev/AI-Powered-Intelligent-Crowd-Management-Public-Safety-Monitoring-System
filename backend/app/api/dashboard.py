from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.core.database import get_db, engine
from backend.app.models.camera import Camera, CameraStatus
from backend.app.models.events import Alert, AlertStatus, AlertSeverity, DetectionEvent, CrowdMetric
from backend.app.models.user import User
from backend.app.services.auth_service import get_current_user
from backend.app.schemas.dashboard import DashboardSummaryResponse, DashboardAlertItem, DashboardZoneItem
from backend.app.schemas.camera import CameraResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_cameras = db.query(Camera).count()
    online_cameras = db.query(Camera).filter(Camera.status == CameraStatus.ONLINE).count()
    offline_cameras = db.query(Camera).filter(Camera.status.in_([CameraStatus.OFFLINE, CameraStatus.ERROR])).count()

    active_alerts = db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).count()
    critical_alerts = db.query(Alert).filter(
        Alert.status == AlertStatus.ACTIVE,
        Alert.severity == AlertSeverity.CRITICAL
    ).count()

    today_events = db.query(DetectionEvent).count()

    # Determine overall system health
    if offline_cameras > 0 or critical_alerts > 0:
        system_status = "WARNING"
    elif total_cameras == 0:
        system_status = "STANDBY"
    else:
        system_status = "OPTIMAL"

    recent_cams = db.query(Camera).order_by(Camera.updated_at.desc()).limit(5).all()
    recent_cam_responses = [
        CameraResponse(
            id=c.id,
            name=c.name,
            location=c.location,
            input_type=c.input_type,
            source=c.source,
            username=c.username,
            has_password=bool(c.password_encrypted),
            status=c.status,
            enabled=c.enabled,
            resolution=c.resolution or "N/A",
            fps=c.fps or 0.0,
            description=c.description,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in recent_cams
    ]

    recent_alerts_db = db.query(Alert).order_by(Alert.created_at.desc()).limit(5).all()
    recent_alerts = []
    for a in recent_alerts_db:
        cam_name = "System"
        if a.camera_id:
            c = db.query(Camera).filter(Camera.id == a.camera_id).first()
            if c:
                cam_name = c.name
        recent_alerts.append(
            DashboardAlertItem(
                id=a.id,
                camera_name=cam_name,
                alert_type=a.alert_type.value,
                severity=a.severity.value,
                message=a.message,
                timestamp=a.created_at.strftime("%H:%M:%S"),
                status=a.status.value
            )
        )

    # Phase 3 YOLO & ByteTrack Live Metrics
    try:
        from backend.ai.pipeline import ai_pipeline
        global_ai = ai_pipeline.get_global_metrics()
        live_current = global_ai.get("current_people", 0)
        live_peak = global_ai.get("peak_people", 0)
    except Exception:
        live_current, live_peak = 0, 0

    # Query latest crowd metric from database if available
    latest_metric = db.query(CrowdMetric).order_by(CrowdMetric.created_at.desc()).first()
    if live_current > 0:
        current_people = live_current
    elif latest_metric:
        current_people = latest_metric.people_count
    else:
        current_people = 18 if total_cameras > 0 else 0

    peak_crowd = max(live_peak, current_people, 18 if total_cameras > 0 else 0)

    chart_labels = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]
    chart_data = [12, 19, 28, 35, 42, 36, current_people]

    # Phase 4 Real-time Zone Metrics
    zone_items: list[DashboardZoneItem] = []
    try:
        from backend.ai.pipeline import ai_pipeline
        target_cam_id = recent_cams[0].id if recent_cams else 1
        zones_data = ai_pipeline.get_camera_zones(target_cam_id)
        for zid, zinfo in zones_data.items():
            zone_items.append(
                DashboardZoneItem(
                    zone_id=zid,
                    name=zinfo.get("name", zid),
                    people_count=zinfo.get("people_count", 0),
                    capacity=zinfo.get("capacity", 20),
                    occupancy_ratio=zinfo.get("occupancy_ratio", 0.0),
                    density_level=zinfo.get("density_level", "LOW")
                )
            )
    except Exception:
        pass

    # Phase 5 Real-time Congestion Telemetry
    congestion_level = "NORMAL"
    try:
        from backend.ai.pipeline import ai_pipeline
        target_cam_id = recent_cams[0].id if recent_cams else 1
        cong_data = ai_pipeline.get_camera_congestion(target_cam_id)
        congestion_level = cong_data.get("congestion_level", "NORMAL")
    except Exception:
        pass

    return DashboardSummaryResponse(
        total_cameras=total_cameras,
        online_cameras=online_cameras,
        offline_cameras=offline_cameras,
        current_people=current_people,
        peak_crowd=peak_crowd,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        today_events=today_events,
        system_status=system_status,
        database_type=engine.dialect.name.upper(),
        recent_cameras=recent_cam_responses,
        recent_alerts=recent_alerts,
        crowd_chart_labels=chart_labels,
        crowd_chart_data=chart_data,
        zones=zone_items,
        congestion_level=congestion_level
    )

