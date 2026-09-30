import logging
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.models.camera import Camera, CameraStatus, CameraInputType
from backend.app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse, CameraTestResponse
from backend.app.services.auth_service import get_current_user, require_admin
from backend.app.models.user import User
from backend.app.services.camera_service import camera_service

logger = logging.getLogger("crowd_safety.api.cameras")
router = APIRouter(prefix="/cameras", tags=["Cameras"])

class RawTestRequest(BaseModel):
    input_type: CameraInputType
    source: str
    username: Optional[str] = None
    password: Optional[str] = None

def _camera_to_response(camera: Camera) -> CameraResponse:
    return CameraResponse(
        id=camera.id,
        name=camera.name,
        location=camera.location,
        input_type=camera.input_type,
        source=camera.source,
        username=camera.username,
        has_password=bool(camera.password_encrypted),
        status=camera.status,
        enabled=camera.enabled,
        resolution=camera.resolution or "N/A",
        fps=camera.fps or 0.0,
        description=camera.description,
        created_at=camera.created_at,
        updated_at=camera.updated_at
    )

@router.get("", response_model=List[CameraResponse])
def list_cameras(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Camera)
    if enabled_only:
        query = query.filter(Camera.enabled == True)
    cameras = query.order_by(Camera.id.asc()).all()
    return [_camera_to_response(c) for c in cameras]

@router.post("", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(
    camera_in: CameraCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Verify unique name
    existing = db.query(Camera).filter(Camera.name == camera_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A camera with the name '{camera_in.name}' already exists."
        )

    # Initial test probe to set status
    success, status_result, message, meta = camera_service.test_raw_source(
        input_type=camera_in.input_type,
        source_path=camera_in.source,
        username=camera_in.username,
        password=camera_in.password
    )

    new_camera = Camera(
        name=camera_in.name,
        location=camera_in.location,
        input_type=camera_in.input_type,
        source=camera_in.source,
        username=camera_in.username,
        password_encrypted=camera_in.password,  # Stored server-side, never returned to client
        status=status_result,
        enabled=True,
        resolution=meta.get("resolution", "N/A"),
        fps=meta.get("fps", 0.0),
        description=camera_in.description
    )
    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)
    return _camera_to_response(new_camera)

@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    return _camera_to_response(camera)

@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: int,
    camera_in: CameraUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    if camera_in.name is not None:
        camera.name = camera_in.name
    if camera_in.location is not None:
        camera.location = camera_in.location
    if camera_in.input_type is not None:
        camera.input_type = camera_in.input_type
    if camera_in.source is not None:
        camera.source = camera_in.source
    if camera_in.username is not None:
        camera.username = camera_in.username
    if camera_in.password is not None and camera_in.password != "":
        camera.password_encrypted = camera_in.password
    if camera_in.enabled is not None:
        camera.enabled = camera_in.enabled
        if not camera_in.enabled:
            camera.status = CameraStatus.DISABLED
    if camera_in.description is not None:
        camera.description = camera_in.description

    # Release any active capture so it reconnects with new settings
    camera_service.release_source(camera_id)

    db.commit()
    db.refresh(camera)
    return _camera_to_response(camera)

@router.delete("/{camera_id}", status_code=status.HTTP_200_OK)
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    camera_service.release_source(camera_id)
    db.delete(camera)
    db.commit()
    return {"message": f"Camera '{camera.name}' deleted successfully."}

@router.post("/{camera_id}/test", response_model=CameraTestResponse)
def test_camera_connection(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    success, status_result, message, meta = camera_service.test_camera(camera)
    camera.status = status_result
    if success:
        camera.resolution = meta.get("resolution", camera.resolution)
        camera.fps = meta.get("fps", camera.fps)
    db.commit()

    return CameraTestResponse(
        success=success,
        status=status_result,
        message=message,
        details=meta
    )

@router.post("/test-raw", response_model=CameraTestResponse)
def test_raw_camera(
    request: RawTestRequest,
    current_user: User = Depends(get_current_user)
):
    success, status_result, message, meta = camera_service.test_raw_source(
        input_type=request.input_type,
        source_path=request.source,
        username=request.username,
        password=request.password
    )
    return CameraTestResponse(
        success=success,
        status=status_result,
        message=message,
        details=meta
    )

@router.post("/{camera_id}/enable", response_model=CameraResponse)
def enable_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    camera.enabled = True
    if camera.status == CameraStatus.DISABLED:
        camera.status = CameraStatus.OFFLINE
    db.commit()
    db.refresh(camera)
    return _camera_to_response(camera)

@router.post("/{camera_id}/disable", response_model=CameraResponse)
def disable_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    camera.enabled = False
    camera.status = CameraStatus.DISABLED
    camera_service.release_source(camera_id)
    db.commit()
    db.refresh(camera)
    return _camera_to_response(camera)

@router.get("/{camera_id}/stream")
def stream_camera(
    camera_id: int,
    annotate: bool = Query(default=True, description="Overlay YOLO detection boxes and ByteTrack IDs"),
    heatmap: bool = Query(default=False, description="Overlay spatial crowd density heatmap"),
    db: Session = Depends(get_db)
):
    """
    Non-blocking MJPEG live video stream.
    Can be consumed directly by an HTML <img> tag (e.g. <img src="/api/cameras/1/stream">).
    """
    return StreamingResponse(
        camera_service.stream_mjpeg(camera_id, db, annotate=annotate, heatmap=heatmap),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "close"
        }
    )

@router.get("/{camera_id}/metrics")
def get_camera_ai_metrics(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve real-time Phase 3 AI tracking metrics for a camera node:
    Current people, peak crowd, average movement speed, and active track list.
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    from backend.ai.pipeline import ai_pipeline
    metrics = ai_pipeline.get_camera_metrics(camera_id)
    return metrics

@router.get("/{camera_id}/zones")
def get_camera_zones(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve real-time Phase 4 zone spatial telemetry for a camera channel:
    Zone A, B, C, D headcount, density classification, and occupancy ratio.
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    from backend.ai.pipeline import ai_pipeline
    zones = ai_pipeline.get_camera_zones(camera_id)
    return zones

@router.put("/{camera_id}/zones")
def update_camera_zones(
    camera_id: int,
    zone_capacities: Dict[str, int],
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Configure zone capacities for a camera node.
    Example payload: {"ZONE_A": 20, "ZONE_B": 30, "ZONE_C": 15, "ZONE_D": 25}
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    from backend.ai.pipeline import ai_pipeline
    analyzer = ai_pipeline.get_density_analyzer(camera_id)
    for zid, cap in zone_capacities.items():
        if zid in analyzer.zones and isinstance(cap, int) and cap > 0:
            analyzer.zones[zid].capacity = cap

    return {"message": "Zone capacities updated successfully.", "zones": ai_pipeline.get_camera_zones(camera_id)}

@router.get("/{camera_id}/congestion")
def get_camera_congestion(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve real-time Phase 5 congestion and bottleneck analytics:
    Congestion index, congestion level, stationary pedestrian count,
    spatial clusters, and active bottleneck zones.
    """
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    from backend.ai.pipeline import ai_pipeline
    congestion = ai_pipeline.get_camera_congestion(camera_id)
    return congestion



