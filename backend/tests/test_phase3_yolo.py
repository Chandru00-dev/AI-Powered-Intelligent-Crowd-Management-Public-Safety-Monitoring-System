import os
import cv2
import numpy as np
import pytest
from backend.ai.detection.yolo_detector import YOLODetector
from backend.ai.tracking.tracker import ByteTrackTracker
from backend.ai.detection.annotator import annotate_frame
from backend.ai.crowd.crowd_counter import CrowdCounter
from backend.ai.pipeline import ai_pipeline
from backend.app.core.database import SessionLocal

def test_yolo_detector_initialization():
    detector = YOLODetector()
    assert detector.model is not None
    assert detector.person_class_id == 0

def test_yolo_detection_on_frame():
    detector = YOLODetector()
    # Create test synthetic frame with 2 persons
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)
    # Draw simple human silhouettes
    cv2.circle(frame, (150, 120), 15, (220, 220, 220), -1)
    cv2.rectangle(frame, (135, 140), (165, 230), (180, 140, 90), -1)

    cv2.circle(frame, (350, 120), 15, (220, 220, 220), -1)
    cv2.rectangle(frame, (335, 140), (365, 230), (180, 140, 90), -1)

    detections = detector.detect_persons(frame, conf_threshold=0.1)
    assert isinstance(detections, list)

def test_bytetrack_tracking():
    tracker = ByteTrackTracker()
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (50, 50, 50)
    # Draw person
    cv2.circle(frame, (200, 100), 20, (230, 230, 230), -1)
    cv2.rectangle(frame, (180, 120), (220, 220), (200, 120, 80), -1)

    tracks, metrics = tracker.track(frame)
    assert isinstance(tracks, list)
    assert "current_people" in metrics
    assert "peak_people" in metrics
    assert "average_people" in metrics

def test_frame_annotation():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    tracks = [{
        "id": 1,
        "bbox": [100, 80, 180, 220],
        "confidence": 0.89,
        "movement_speed": 1.2,
        "direction": "EAST",
        "history": [(140, 150), (145, 150)]
    }]
    metrics = {"current_people": 1, "peak_people": 5}
    annotated = annotate_frame(frame, tracks, metrics, fps=24.0)
    assert annotated.shape == (360, 640, 3)

def test_crowd_counter_db_persistence():
    db = SessionLocal()
    counter = CrowdCounter(camera_id=1)
    counter.persist_interval_sec = 0.0  # Force immediate persist for test
    counter.record_metrics(db, current_people=22, average_movement_speed=1.5)
    db.close()

def test_ai_pipeline_end_to_end():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    annotated, metrics = ai_pipeline.process_camera_frame(
        camera_id=99,
        frame=frame,
        annotate=True
    )
    assert annotated is not None
    assert "current_people" in metrics
    assert "fps" in metrics
