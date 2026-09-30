import os
import time
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger("crowd_safety.ai.yolo")

class YOLODetector:
    """
    Singleton wrapper for Ultralytics YOLOv8 pedestrian detector.
    Extracts person bounding boxes, confidences, and coordinates.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(YOLODetector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path: str = None):
        if self._initialized:
            return

        if model_path is None:
            # Look in models/pretrained/yolov8n.pt
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            model_path = os.path.join(base_dir, "models", "pretrained", "yolov8n.pt")

        self.model_path = model_path
        logger.info(f"Loading YOLO model from {self.model_path}...")
        self.model = YOLO(self.model_path)
        # Class 0 is 'person' in standard COCO dataset
        self.person_class_id = 0
        self._initialized = True
        logger.info("YOLOv8 Pedestrian Detector initialized.")

    def detect_persons(self, frame: np.ndarray, conf_threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        Run inference on frame and extract detected persons.
        Returns list of detections with bbox, confidence, class, and timestamp.
        """
        results = self.model.predict(
            source=frame,
            classes=[self.person_class_id],
            conf=conf_threshold,
            verbose=False
        )

        detections = []
        frame_timestamp = time.time()

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                detections.append({
                    "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                    "confidence": round(conf, 3),
                    "class": "person",
                    "timestamp": frame_timestamp,
                    "center": [round((x1 + x2) / 2.0, 1), round((y1 + y2) / 2.0, 1)]
                })

        return detections
