import time
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.camera import Camera, CameraInputType, CameraStatus
from backend.ai.congestion.congestion_analyzer import CongestionAnalyzer, PedestrianState
from backend.ai.crowd.density_analyzer import DensityAnalyzer
from backend.ai.detection.annotator import annotate_frame
from backend.ai.pipeline import ai_pipeline

client = TestClient(app)

@pytest.fixture
def admin_token():
    res = client.post("/api/auth/login", json={
        "email": settings.DEFAULT_ADMIN_EMAIL,
        "password": settings.DEFAULT_ADMIN_PASSWORD
    })
    return res.json()["access_token"]

@pytest.fixture
def test_camera_id():
    db = SessionLocal()
    try:
        cam = db.query(Camera).first()
        if not cam:
            cam = Camera(
                name="Phase 5 Test Camera",
                location="North Terminal Corridor",
                input_type=CameraInputType.VIDEO_FILE,
                source="frontend/assets/samples/sample_crowd.mp4",
                status=CameraStatus.ONLINE,
                enabled=True
            )
            db.add(cam)
            db.commit()
            db.refresh(cam)
        return cam.id
    finally:
        db.close()

def test_pedestrian_state_tracking():
    now = time.time()
    p = PedestrianState(track_id=1, initial_pos=(100.0, 100.0), timestamp=now)
    assert p.is_stationary is False
    assert p.dwell_time == 0.0

    # Simulate fast movement
    p.update(current_pos=(150.0, 150.0), speed=12.0, timestamp=now + 1.0)
    assert p.is_stationary is False

    # Simulate stopping at same spot
    p.update(current_pos=(151.0, 150.0), speed=1.0, timestamp=now + 2.0)
    assert p.is_stationary is False  # Only 0 seconds stopped so far

    # Continue stationary for > 3.0 seconds
    p.update(current_pos=(151.0, 150.5), speed=0.5, timestamp=now + 5.5)
    assert p.is_stationary is True
    assert p.dwell_time >= 3.0

def test_congestion_analyzer_normal_flow():
    analyzer = CongestionAnalyzer(camera_id=101)
    tracks = [
        {"id": 1, "bbox": [50, 50, 90, 150], "movement_speed": 15.0},
        {"id": 2, "bbox": [200, 100, 240, 200], "movement_speed": 12.0},
        {"id": 3, "bbox": [350, 120, 390, 220], "movement_speed": 18.0}
    ]
    telemetry = analyzer.analyze_congestion(tracks)
    assert telemetry["congestion_level"] == "NORMAL"
    assert telemetry["congestion_index"] == 0.0
    assert telemetry["stationary_count"] == 0
    assert telemetry["moving_count"] == 3
    assert len(telemetry["clusters"]) == 0

def test_congestion_analyzer_stationary_clustering():
    analyzer = CongestionAnalyzer(camera_id=102, min_cluster_size=3)
    density_analyzer = DensityAnalyzer(camera_id=102)
    zones = density_analyzer.analyze_zones((360, 640), [])

    now = time.time()
    # 3 stationary pedestrians clustered closely together in Zone A (top-left)
    tracks = [
        {"id": 10, "bbox": [100, 80, 140, 160], "movement_speed": 0.5},
        {"id": 11, "bbox": [120, 90, 160, 170], "movement_speed": 0.2},
        {"id": 12, "bbox": [110, 85, 150, 165], "movement_speed": 0.1},
    ]

    # Initialize states
    analyzer.analyze_congestion(tracks, zones)

    # Fast forward time by simulating stationary presence for 4 seconds
    for trk in tracks:
        tid = trk["id"]
        analyzer.pedestrians[tid].stationary_since = now - 5.0
        analyzer.pedestrians[tid].dwell_time = 5.0
        analyzer.pedestrians[tid].is_stationary = True

    telemetry = analyzer.analyze_congestion(tracks, zones)
    assert telemetry["stationary_count"] == 3
    assert telemetry["congestion_index"] >= 0.50
    assert telemetry["congestion_level"] in ("CONGESTED", "SEVERE")
    assert len(telemetry["clusters"]) >= 1
    assert "Zone A" in telemetry["clusters"][0]["zone"]
    assert "Zone A: Main Entrance" in telemetry["bottleneck_zones"]

def test_congestion_alert_triggering():
    analyzer = CongestionAnalyzer(camera_id=103)
    tracks = [
        {"id": 1, "bbox": [100, 80, 140, 160], "movement_speed": 0.0},
        {"id": 2, "bbox": [110, 85, 150, 165], "movement_speed": 0.0},
        {"id": 3, "bbox": [120, 90, 160, 170], "movement_speed": 0.0},
    ]

    analyzer.analyze_congestion(tracks)
    now = time.time()
    for trk in tracks:
        tid = trk["id"]
        analyzer.pedestrians[tid].stationary_since = now - 5.0
        analyzer.pedestrians[tid].is_stationary = True

    # Pre-set consecutive congestion start time to simulate 5 seconds of congestion
    analyzer.consecutive_congested_start = now - 5.0

    telemetry = analyzer.analyze_congestion(tracks)
    alert = telemetry["active_alert"]
    assert alert is not None
    assert alert["alert_type"] == "CONGESTION"
    assert "Congestion detected" in alert["message"]

def test_annotator_with_congestion():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    tracks = [
        {"id": 1, "bbox": [100, 80, 140, 160], "confidence": 0.9, "movement_speed": 0.0, "is_stationary": True, "dwell_time": 8.0}
    ]
    metrics = {"current_people": 1, "peak_people": 1}
    congestion = {
        "congestion_index": 0.65,
        "congestion_level": "CONGESTED",
        "bottleneck_zones": ["Zone A: Main Entrance"],
        "clusters": [
            {
                "cluster_id": 1,
                "member_ids": [1],
                "center": (120.0, 160.0),
                "radius": 40.0,
                "severity": "HIGH"
            }
        ]
    }

    annotated = annotate_frame(frame, tracks, metrics, fps=24.0, congestion=congestion)
    assert annotated.shape == (360, 640, 3)

def test_get_camera_congestion_endpoint(admin_token, test_camera_id):
    res = client.get(
        f"/api/cameras/{test_camera_id}/congestion",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "congestion_index" in data
    assert "congestion_level" in data
    assert "stationary_count" in data
    assert "moving_count" in data
    assert "clusters" in data
    assert "bottleneck_zones" in data

def test_dashboard_summary_includes_congestion_level(admin_token):
    res = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    summary = res.json()
    assert "congestion_level" in summary
    assert summary["congestion_level"] in ("NORMAL", "MODERATE", "CONGESTED", "SEVERE")
