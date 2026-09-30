import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings

client = TestClient(app)

@pytest.fixture
def admin_token():
    res = client.post("/api/auth/login", json={
        "email": settings.DEFAULT_ADMIN_EMAIL,
        "password": settings.DEFAULT_ADMIN_PASSWORD
    })
    return res.json()["access_token"]

def test_list_cameras(admin_token):
    res = client.get("/api/cameras", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    cameras = res.json()
    assert isinstance(cameras, list)

def test_create_and_manage_camera(admin_token):
    # 1. Create a video camera node
    cam_data = {
        "name": "Test Plaza Corridor",
        "location": "Plaza Floor 2",
        "input_type": "VIDEO_FILE",
        "source": "frontend/assets/samples/sample_crowd.mp4",
        "description": "Automated testing camera node"
    }
    create_res = client.post(
        "/api/cameras",
        json=cam_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_res.status_code == 201
    cam = create_res.json()
    cam_id = cam["id"]
    assert cam["name"] == "Test Plaza Corridor"
    assert cam["has_password"] is False

    # 2. Test Connection on the created camera
    test_res = client.post(
        f"/api/cameras/{cam_id}/test",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert test_res.status_code == 200
    test_data = test_res.json()
    assert "success" in test_data
    assert "status" in test_data

    # 3. Disable camera
    dis_res = client.post(
        f"/api/cameras/{cam_id}/disable",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert dis_res.status_code == 200
    assert dis_res.json()["enabled"] is False

    # 4. Enable camera
    en_res = client.post(
        f"/api/cameras/{cam_id}/enable",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert en_res.status_code == 200
    assert en_res.json()["enabled"] is True

    # 5. Delete camera
    del_res = client.delete(
        f"/api/cameras/{cam_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_res.status_code == 200

def test_invalid_rtsp_connection_handling(admin_token):
    # Probing an invalid or unreachable RTSP stream should not crash
    raw_res = client.post(
        "/api/cameras/test-raw",
        json={
            "input_type": "RTSP",
            "source": "rtsp://nonexistent.cctv.local:554/stream"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert raw_res.status_code == 200
    data = raw_res.json()
    assert data["success"] is False
    assert data["status"] == "OFFLINE"
    assert "Unable to establish connection" in data["message"]
