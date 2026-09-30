import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.events import ZoneMetric
from backend.app.models.camera import Camera, CameraInputType, CameraStatus
from backend.ai.crowd.density_analyzer import DensityAnalyzer, ZoneConfig
from backend.ai.detection.annotator import annotate_frame

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
                name="Test Phase 4 Cam",
                location="Main Gate",
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

def test_zone_config_containment():
    zone = ZoneConfig("ZONE_TEST", "Test Quadrant", (0.0, 0.0, 0.5, 0.5), capacity=20)
    assert zone.contains((0.25, 0.25)) is True
    assert zone.contains((0.0, 0.0)) is True
    assert zone.contains((0.5, 0.5)) is True
    assert zone.contains((0.75, 0.25)) is False
    assert zone.contains((0.25, 0.75)) is False

def test_density_analyzer_classification():
    analyzer = DensityAnalyzer(camera_id=999)
    # Capacity = 20
    # 0/20 = 0.0 -> LOW
    lvl, ratio = analyzer.classify_density(0, 20)
    assert lvl == "LOW"
    assert ratio == 0.0

    # 4/20 = 0.20 -> LOW (<0.30)
    lvl, ratio = analyzer.classify_density(4, 20)
    assert lvl == "LOW"
    assert ratio == 0.20

    # 8/20 = 0.40 -> MEDIUM (0.30 to 0.65)
    lvl, ratio = analyzer.classify_density(8, 20)
    assert lvl == "MEDIUM"
    assert ratio == 0.40

    # 14/20 = 0.70 -> HIGH (0.65 to 0.85)
    lvl, ratio = analyzer.classify_density(14, 20)
    assert lvl == "HIGH"
    assert ratio == 0.70

    # 18/20 = 0.90 -> CRITICAL (>=0.85)
    lvl, ratio = analyzer.classify_density(18, 20)
    assert lvl == "CRITICAL"
    assert ratio == 0.90

def test_density_analyzer_quadrant_mapping():
    analyzer = DensityAnalyzer(camera_id=999)
    # 640x360 frame
    # Place 1 person in Zone A (Top-Left: x < 320, y < 180)
    # Place 2 persons in Zone D (Bottom-Right: x > 320, y > 180)
    tracks = [
        {"bbox": [50, 50, 90, 150]},     # foot at (70, 150) -> norm (70/640=0.109, 150/360=0.416) -> Zone A
        {"bbox": [400, 200, 450, 300]}, # foot at (425, 300) -> norm (425/640=0.664, 300/360=0.833) -> Zone D
        {"bbox": [500, 220, 550, 320]}, # foot at (525, 320) -> norm (525/640=0.820, 320/360=0.888) -> Zone D
    ]
    results = analyzer.analyze_zones((360, 640), tracks)
    assert results["ZONE_A"]["people_count"] == 1
    assert results["ZONE_B"]["people_count"] == 0
    assert results["ZONE_C"]["people_count"] == 0
    assert results["ZONE_D"]["people_count"] == 2

def test_density_analyzer_heatmap_generation():
    analyzer = DensityAnalyzer(camera_id=999)
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (30, 30, 30)

    tracks = [
        {"bbox": [100, 100, 150, 250]},
        {"bbox": [120, 110, 170, 260]},
        {"bbox": [400, 150, 450, 300]}
    ]

    heatmap_frame = analyzer.generate_heatmap_overlay(frame, tracks)
    assert heatmap_frame.shape == (360, 640, 3)
    assert heatmap_frame.dtype == np.uint8
    # Ensure pixels were modified by the overlay
    assert not np.array_equal(heatmap_frame, frame)

def test_density_analyzer_db_persistence(test_camera_id):
    analyzer = DensityAnalyzer(camera_id=test_camera_id)
    analyzer.last_persist_time = 0.0  # force persist immediately

    db = SessionLocal()
    try:
        tracks = [{"bbox": [50, 50, 100, 150]}]
        analyzer.analyze_zones((360, 640), tracks, db=db)

        # Check that zone_metrics records were created
        records = db.query(ZoneMetric).filter(ZoneMetric.camera_id == test_camera_id).all()
        assert len(records) >= 4
    finally:
        db.close()

def test_frame_annotation_with_zones():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    analyzer = DensityAnalyzer(camera_id=1)
    tracks = [{"id": 1, "bbox": [50, 50, 100, 150], "confidence": 0.95}]
    metrics = {"current_people": 1, "peak_people": 2}
    zones = analyzer.analyze_zones((360, 640), tracks)

    annotated = annotate_frame(frame, tracks, metrics, fps=25.0, zones=zones)
    assert annotated.shape == (360, 640, 3)

def test_get_camera_zones_endpoint(admin_token, test_camera_id):
    res = client.get(
        f"/api/cameras/{test_camera_id}/zones",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    zones = res.json()
    assert "ZONE_A" in zones
    assert "ZONE_B" in zones
    assert "ZONE_C" in zones
    assert "ZONE_D" in zones
    assert "people_count" in zones["ZONE_A"]
    assert "density_level" in zones["ZONE_A"]

def test_update_camera_zones_endpoint(admin_token, test_camera_id):
    update_payload = {
        "ZONE_A": 35,
        "ZONE_B": 45
    }
    res = client.put(
        f"/api/cameras/{test_camera_id}/zones",
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "zones" in data
    assert data["zones"]["ZONE_A"]["capacity"] == 35
    assert data["zones"]["ZONE_B"]["capacity"] == 45

def test_dashboard_summary_zones(admin_token):
    res = client.get(
        "/api/dashboard/summary",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    summary = res.json()
    assert "zones" in summary
    assert isinstance(summary["zones"], list)
