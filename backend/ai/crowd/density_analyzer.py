import logging
from typing import Dict, List, Tuple, Any, Optional
import cv2
import numpy as np
from sqlalchemy.orm import Session
from backend.app.models.events import ZoneMetric
from backend.app.core.config import settings

logger = logging.getLogger("crowd_safety.ai.density")

class ZoneConfig:
    def __init__(self, zone_id: str, name: str, bbox_norm: Tuple[float, float, float, float], capacity: int = 25):
        self.zone_id = zone_id
        self.name = name
        # Normalized coordinates: (x_min, y_min, x_max, y_max) between 0.0 and 1.0
        self.bbox_norm = bbox_norm
        self.capacity = capacity

    def contains(self, point_norm: Tuple[float, float]) -> bool:
        x, y = point_norm
        x1, y1, x2, y2 = self.bbox_norm
        return x1 <= x <= x2 and y1 <= y <= y2


class DensityAnalyzer:
    """
    Analyzes spatial distribution of pedestrians across configurable zones.
    Computes density index, occupancy ratios, and spatial heatmaps.
    """
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        # Standard 4 surveillance quadrants
        self.zones: Dict[str, ZoneConfig] = {
            "ZONE_A": ZoneConfig("ZONE_A", "Zone A: Main Entrance", (0.0, 0.0, 0.5, 0.5), capacity=15),
            "ZONE_B": ZoneConfig("ZONE_B", "Zone B: Concourse Plaza", (0.5, 0.0, 1.0, 0.5), capacity=20),
            "ZONE_C": ZoneConfig("ZONE_C", "Zone C: Escalator Corridor", (0.0, 0.5, 0.5, 1.0), capacity=12),
            "ZONE_D": ZoneConfig("ZONE_D", "Zone D: South Exit Gate", (0.5, 0.5, 1.0, 1.0), capacity=18),
        }
        self.last_persist_time: float = 0.0
        self.persist_interval_sec: float = 12.0

    def classify_density(self, count: int, capacity: int) -> Tuple[str, float]:
        """
        Classify density: LOW, MEDIUM, HIGH, CRITICAL based on occupancy ratio.
        """
        ratio = count / max(capacity, 1)
        if ratio >= 0.85:
            return "CRITICAL", round(ratio, 2)
        elif ratio >= 0.65:
            return "HIGH", round(ratio, 2)
        elif ratio >= 0.30:
            return "MEDIUM", round(ratio, 2)
        else:
            return "LOW", round(ratio, 2)

    def analyze_zones(
        self,
        frame_shape: Tuple[int, int],
        tracks: List[Dict[str, Any]],
        db: Optional[Session] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Maps pedestrians to zones and returns structured zone telemetry.
        """
        height, width = frame_shape[:2]
        zone_counts = {zid: 0 for zid in self.zones}

        # Count pedestrians inside each zone
        for trk in tracks:
            # Use feet position (bottom center of bounding box) for ground-plane accuracy
            bbox = trk["bbox"]
            foot_x = (bbox[0] + bbox[2]) / 2.0
            foot_y = float(bbox[3])

            norm_x = min(max(foot_x / max(width, 1), 0.0), 1.0)
            norm_y = min(max(foot_y / max(height, 1), 0.0), 1.0)

            for zid, zone in self.zones.items():
                if zone.contains((norm_x, norm_y)):
                    zone_counts[zid] += 1
                    break

        # Build telemetry summary
        results = {}
        for zid, zone in self.zones.items():
            cnt = zone_counts[zid]
            level, ratio = self.classify_density(cnt, zone.capacity)
            x1 = int(zone.bbox_norm[0] * width)
            y1 = int(zone.bbox_norm[1] * height)
            x2 = int(zone.bbox_norm[2] * width)
            y2 = int(zone.bbox_norm[3] * height)

            results[zid] = {
                "zone_id": zid,
                "name": zone.name,
                "people_count": cnt,
                "capacity": zone.capacity,
                "occupancy_ratio": ratio,
                "density_level": level,
                "pixel_bounds": (x1, y1, x2, y2)
            }

        # Periodically write to database in batch
        if db is not None:
            self._persist_all_zone_metrics(db, results)

        return results

    def _persist_all_zone_metrics(self, db: Session, results: Dict[str, Dict[str, Any]]):
        import time
        now = time.time()
        if now - self.last_persist_time >= self.persist_interval_sec:
            try:
                for zid, zdata in results.items():
                    record = ZoneMetric(
                        camera_id=self.camera_id,
                        zone_name=zdata["name"],
                        people_count=zdata["people_count"],
                        density_level=zdata["density_level"]
                    )
                    db.add(record)
                db.commit()
                self.last_persist_time = now
            except Exception as e:
                db.rollback()
                logger.error(f"Error persisting zone metrics: {e}")

    def generate_heatmap_overlay(self, frame: np.ndarray, tracks: List[Dict[str, Any]]) -> np.ndarray:
        """
        Renders a semi-transparent spatial crowd density heatmap overlay
        representing crowd concentration areas.
        """
        h, w = frame.shape[:2]
        density_map = np.zeros((h, w), dtype=np.float32)

        for trk in tracks:
            bbox = trk["bbox"]
            cx = int((bbox[0] + bbox[2]) / 2.0)
            cy = int(bbox[3])  # feet level

            # Add Gaussian blob around pedestrian location
            radius = 35
            cv2.circle(density_map, (cx, cy), radius, 1.0, -1)

        # Smooth density map
        density_map = cv2.GaussianBlur(density_map, (45, 45), 0)
        max_val = np.max(density_map)
        if max_val > 0:
            density_map = (density_map / max_val * 255).astype(np.uint8)
        else:
            density_map = density_map.astype(np.uint8)

        # Apply color map: Blue (Cold) -> Cyan -> Yellow -> Red (Dense)
        heatmap_color = cv2.applyColorMap(density_map, cv2.COLORMAP_JET)

        # Blend where heat is present
        mask = density_map > 15
        blended = frame.copy()
        blended[mask] = cv2.addWeighted(frame, 0.55, heatmap_color, 0.45, 0)[mask]
        return blended
