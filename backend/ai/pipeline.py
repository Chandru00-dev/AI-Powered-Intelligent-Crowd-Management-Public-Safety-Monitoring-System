import time
import logging
from typing import Dict, Tuple, Any
import numpy as np
from sqlalchemy.orm import Session

from backend.ai.tracking.tracker import ByteTrackTracker
from backend.ai.detection.annotator import annotate_frame
from backend.ai.crowd.crowd_counter import CrowdCounter
from backend.ai.crowd.density_analyzer import DensityAnalyzer
from backend.ai.congestion.congestion_analyzer import CongestionAnalyzer

logger = logging.getLogger("crowd_safety.ai.pipeline")

class AIPipeline:
    def __init__(self):
        # camera_id -> ByteTrackTracker
        self._trackers: Dict[int, ByteTrackTracker] = {}
        # camera_id -> CrowdCounter
        self._counters: Dict[int, CrowdCounter] = {}
        # camera_id -> DensityAnalyzer
        self._density_analyzers: Dict[int, DensityAnalyzer] = {}
        # camera_id -> CongestionAnalyzer
        self._congestion_analyzers: Dict[int, CongestionAnalyzer] = {}
        self._last_fps_calc: Dict[int, Tuple[float, int, float]] = {} # camera_id -> (last_time, frame_count, current_fps)
        self._latest_congestion: Dict[int, Dict[str, Any]] = {}

    def get_tracker(self, camera_id: int) -> ByteTrackTracker:
        if camera_id not in self._trackers:
            self._trackers[camera_id] = ByteTrackTracker()
            self._counters[camera_id] = CrowdCounter(camera_id)
            self._density_analyzers[camera_id] = DensityAnalyzer(camera_id)
            self._congestion_analyzers[camera_id] = CongestionAnalyzer(camera_id)
            self._last_fps_calc[camera_id] = (time.time(), 0, 20.0)
            self._latest_congestion[camera_id] = {
                "congestion_index": 0.0,
                "congestion_level": "NORMAL",
                "total_pedestrians": 0,
                "stationary_count": 0,
                "moving_count": 0,
                "clusters": [],
                "bottleneck_zones": [],
                "active_alert": None
            }
        return self._trackers[camera_id]

    def get_density_analyzer(self, camera_id: int) -> DensityAnalyzer:
        self.get_tracker(camera_id)
        return self._density_analyzers[camera_id]

    def get_congestion_analyzer(self, camera_id: int) -> CongestionAnalyzer:
        self.get_tracker(camera_id)
        return self._congestion_analyzers[camera_id]

    def process_camera_frame(
        self,
        camera_id: int,
        frame: np.ndarray,
        db: Session = None,
        annotate: bool = True,
        heatmap: bool = False
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        tracker = self.get_tracker(camera_id)
        counter = self._counters[camera_id]
        density_analyzer = self._density_analyzers[camera_id]
        congestion_analyzer = self._congestion_analyzers[camera_id]

        # Calculate live FPS
        now = time.time()
        last_t, f_count, cur_fps = self._last_fps_calc[camera_id]
        f_count += 1
        if now - last_t >= 1.0:
            cur_fps = f_count / (now - last_t)
            self._last_fps_calc[camera_id] = (now, 0, cur_fps)
        else:
            self._last_fps_calc[camera_id] = (last_t, f_count, cur_fps)

        # Run ByteTrack tracking & detection
        tracks, metrics = tracker.track(frame)
        metrics["fps"] = round(cur_fps, 1)

        # Phase 4 Spatial Zone Analysis
        zone_telemetry = density_analyzer.analyze_zones(frame.shape, tracks, db)
        metrics["zones"] = zone_telemetry

        # Phase 5 Congestion & Bottleneck Analysis
        congestion_telemetry = congestion_analyzer.analyze_congestion(tracks, zones=zone_telemetry)
        metrics["congestion"] = congestion_telemetry
        self._latest_congestion[camera_id] = congestion_telemetry

        # Calculate average speed of moving people
        speeds = [t["movement_speed"] for t in tracks if t["movement_speed"] > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        metrics["average_speed"] = round(avg_speed, 1)

        # Persist metric to DB periodically (if DB session provided)
        if db is not None:
            counter.record_metrics(db, metrics["current_people"], avg_speed)

        # Render optional heatmap
        render_frame = frame
        if heatmap:
            render_frame = density_analyzer.generate_heatmap_overlay(frame, tracks)

        # Annotate visual frame with bounding boxes, zone lines, congestion clusters, and HUD
        if annotate:
            annotated_frame = annotate_frame(
                frame=render_frame,
                tracks=tracks,
                metrics=metrics,
                fps=cur_fps,
                zones=zone_telemetry,
                congestion=congestion_telemetry
            )
            return annotated_frame, metrics

        return render_frame, metrics

    def get_global_metrics(self) -> Dict[str, int]:
        """Aggregate current real-time metrics across all active cameras."""
        total_curr = sum(t.current_people for t in self._trackers.values())
        peak_curr = max((t.peak_people for t in self._trackers.values()), default=0)
        return {
            "current_people": total_curr,
            "peak_people": peak_curr
        }

    def get_camera_metrics(self, camera_id: int) -> Dict[str, Any]:
        """Detailed real-time Phase 3 metrics for a specific camera channel."""
        if camera_id in self._trackers:
            tracker = self._trackers[camera_id]
            now = time.time()
            active_people = [
                {
                    "id": tid,
                    "position": (round(p.current_pos[0], 1), round(p.current_pos[1], 1)),
                    "direction": p.direction,
                    "movement_speed": p.movement_speed,
                    "duration_sec": round(now - p.first_seen, 1)
                }
                for tid, p in tracker.tracked_persons.items()
                if now - p.last_seen < 3.0
            ]
            return {
                "camera_id": camera_id,
                "current_people": tracker.current_people,
                "peak_people": tracker.peak_people,
                "total_unique_seen": len(tracker.all_time_unique_ids),
                "fps": round(self._last_fps_calc.get(camera_id, (0, 0, 20.0))[2], 1),
                "active_tracks": active_people
            }

        return {
            "camera_id": camera_id,
            "current_people": 0,
            "peak_people": 0,
            "total_unique_seen": 0,
            "fps": 0.0,
            "active_tracks": []
        }

    def get_camera_zones(self, camera_id: int) -> Dict[str, Any]:
        """Detailed real-time Phase 4 zone breakdown for a camera channel."""
        analyzer = self.get_density_analyzer(camera_id)
        # Use latest tracker tracks if available
        tracker = self.get_tracker(camera_id)
        now = time.time()
        tracks = [
            {"bbox": [int(p.current_pos[0]-15), int(p.current_pos[1]-30), int(p.current_pos[0]+15), int(p.current_pos[1])]}
            for p in tracker.tracked_persons.values()
            if now - p.last_seen < 3.0
        ]
        return analyzer.analyze_zones((360, 640), tracks)

    def get_camera_congestion(self, camera_id: int) -> Dict[str, Any]:
        """Detailed real-time Phase 5 congestion & bottleneck telemetry."""
        self.get_tracker(camera_id)
        return self._latest_congestion.get(camera_id, {
            "congestion_index": 0.0,
            "congestion_level": "NORMAL",
            "total_pedestrians": 0,
            "stationary_count": 0,
            "moving_count": 0,
            "clusters": [],
            "bottleneck_zones": [],
            "active_alert": None
        })

ai_pipeline = AIPipeline()
