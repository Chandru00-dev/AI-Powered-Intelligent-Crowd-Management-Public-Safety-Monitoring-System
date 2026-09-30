import os
import pytest
from backend.app.models.camera import CameraInputType
from backend.app.services.video_source import (
    create_video_source,
    VideoFileSource,
    WebcamSource,
    RTSPSource,
    generate_status_frame
)

def test_video_file_source():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sample_video = os.path.join(project_root, "frontend", "assets", "samples", "sample_crowd.mp4")

    # If file exists, test connection and frame reading
    if os.path.exists(sample_video):
        source = VideoFileSource(source=sample_video, name="Test Sample Video")
        success, msg, meta = source.test_connection()
        assert success is True
        assert "resolution" in meta
        assert meta["fps"] > 0

        # Test frame reading and looping
        connected = source.connect()
        assert connected is True
        ret, frame = source.read_frame()
        assert ret is True
        assert frame is not None
        assert frame.shape[0] > 0
        source.disconnect()
        assert source.is_connected is False

def test_nonexistent_video_file_handling():
    source = VideoFileSource(source="invalid_nonexistent_file_path.mp4", name="Ghost Cam")
    success, msg, meta = source.test_connection()
    assert success is False
    assert "Unable to establish connection" in msg

def test_generate_status_frame():
    frame = generate_status_frame("CAM-01", "OFFLINE", "Test reason")
    assert frame is not None
    assert frame.shape == (360, 640, 3)
