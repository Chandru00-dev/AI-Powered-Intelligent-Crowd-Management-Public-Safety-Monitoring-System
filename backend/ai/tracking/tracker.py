import time
import math
import logging
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger("crowd_safety.ai.tracker")

class TrackedPerson:
    def __init__(self, track_id: int, initial_pos: Tuple[float, float], timestamp: float):
        self.track_id = track_id
        self.current_pos = initial_pos
        self.previous_pos = initial_pos
        self.positions_history = [initial_pos]
        self.first_seen = timestamp
        self.last_seen = timestamp
        self.direction = "STATIONARY"
        self.movement_speed = 0.0  # pixels per second
        self.velocity = (0.0, 0.0)

    def update(self, new_pos: Tuple[float, float], timestamp: float):
        dt = max(timestamp - self.last_seen, 0.001)
        self.previous_pos = self.current_pos
        self.current_pos = new_pos
        self.positions_history.append(new_pos)
        if len(self.positions_history) > 30:
            self.positions_history.pop(0)

        dx = new_pos[0] - self.previous_pos[0]
        dy = new_pos[1] - self.previous_pos[1]
        distance = math.hypot(dx, dy)
        self.movement_speed = round(distance / dt, 1)
        self.velocity = (round(dx / dt, 1), round(dy / dt, 1))

        # Classify heading direction
        if distance > 2.0:
            angle = math.atan2(-dy, dx) * 180 / math.pi
            if -45 <= angle <= 45:
                self.direction = "EAST"
            elif 45 < angle <= 135:
                self.direction = "NORTH"
            elif -135 <= angle < -45:
                self.direction = "SOUTH"
            else:
                self.direction = "WEST"
        else:
            self.direction = "STATIONARY"

        self.last_seen = timestamp


class ByteTrackTracker:
    """
    ByteTrack-based multi-object person tracker.
    Maintains persistent IDs, motion trajectories, velocities,
    and calculates accurate real-time headcount.
    """
    def __init__(self, model_path: str = None):
        self.detector = YOLO(model_path or "models/pretrained/yolov8n.pt")
        self.tracked_persons: Dict[int, TrackedPerson] = {}
        self.all_time_unique_ids = set()
        self.current_people: int = 0
        self.peak_people: int = 0
        self.total_counted: int = 0
        self.history_headcount: List[int] = []

    def track(self, frame: np.ndarray) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Run ByteTrack tracking on incoming camera frame.
        Returns:
            tracked_boxes: List of tracked persons with ID, bbox, and trajectory
            metrics: Headcount metrics (current, peak, average)
        """
        now = time.time()
        # Track persons (class 0) using ByteTrack
        results = self.detector.track(
            source=frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=0.25,
            verbose=False
        )

        active_tracks = []
        active_ids_this_frame = set()

        if results and len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                # Track ID assigned by ByteTrack
                track_id = int(box.id[0]) if box.id is not None else None
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                if track_id is not None:
                    active_ids_this_frame.add(track_id)
                    self.all_time_unique_ids.add(track_id)

                    if track_id not in self.tracked_persons:
                        self.tracked_persons[track_id] = TrackedPerson(track_id, (cx, cy), now)
                    else:
                        self.tracked_persons[track_id].update((cx, cy), now)

                    person_obj = self.tracked_persons[track_id]

                    active_tracks.append({
                        "id": track_id,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": round(conf, 2),
                        "position": (round(cx, 1), round(cy, 1)),
                        "direction": person_obj.direction,
                        "movement_speed": person_obj.movement_speed,
                        "duration_sec": round(now - person_obj.first_seen, 1),
                        "history": person_obj.positions_history
                    })
                else:
                    # Detection without confirmed track ID yet
                    active_tracks.append({
                        "id": -1,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "confidence": round(conf, 2),
                        "position": (round(cx, 1), round(cy, 1)),
                        "direction": "UNKNOWN",
                        "movement_speed": 0.0,
                        "duration_sec": 0.0,
                        "history": []
                    })

        # Update headcount metrics
        self.current_people = len(active_ids_this_frame) if len(active_ids_this_frame) > 0 else len(active_tracks)
        if self.current_people > self.peak_people:
            self.peak_people = self.current_people

        self.history_headcount.append(self.current_people)
        if len(self.history_headcount) > 100:
            self.history_headcount.pop(0)

        avg_people = round(sum(self.history_headcount) / max(len(self.history_headcount), 1), 1)

        # Cleanup lost tracks older than 10 seconds
        stale_threshold = now - 10.0
        self.tracked_persons = {
            tid: p for tid, p in self.tracked_persons.items() if p.last_seen > stale_threshold
        }

        metrics = {
            "current_people": self.current_people,
            "peak_people": self.peak_people,
            "average_people": avg_people,
            "total_unique_seen": len(self.all_time_unique_ids)
        }

        return active_tracks, metrics
