import time
import math
import logging
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger("crowd_safety.ai.congestion")

class PedestrianState:
    """
    Tracks dwell time and displacement history for a single ByteTrack ID.
    """
    def __init__(self, track_id: int, initial_pos: Tuple[float, float], timestamp: float):
        self.track_id = track_id
        self.positions: List[Tuple[float, float, float]] = [(initial_pos[0], initial_pos[1], timestamp)] # x, y, t
        self.first_seen: float = timestamp
        self.last_seen: float = timestamp
        self.stationary_since: Optional[float] = None
        self.is_stationary: bool = False
        self.dwell_time: float = 0.0

    def update(self, current_pos: Tuple[float, float], speed: float, timestamp: float, stationary_threshold: float = 4.0):
        self.last_seen = timestamp
        self.positions.append((current_pos[0], current_pos[1], timestamp))

        # Keep last 15 seconds of trajectory history
        cutoff = timestamp - 15.0
        self.positions = [p for p in self.positions if p[2] >= cutoff]

        # Calculate instantaneous speed from previous position
        if len(self.positions) >= 2:
            prev = self.positions[-2]
            dx = current_pos[0] - prev[0]
            dy = current_pos[1] - prev[1]
            dt = max(timestamp - prev[2], 0.05)
            inst_speed = math.sqrt(dx * dx + dy * dy) / dt
        else:
            inst_speed = speed

        # Evaluate if individual is stationary (low speed and low instantaneous displacement)
        if speed < stationary_threshold and inst_speed < (stationary_threshold * 1.5):
            if self.stationary_since is None:
                self.stationary_since = timestamp
            self.dwell_time = timestamp - self.stationary_since
            self.is_stationary = self.dwell_time >= 3.0  # Stationary after 3 continuous seconds
        else:
            self.stationary_since = None
            self.dwell_time = 0.0
            self.is_stationary = False



class CongestionCluster:
    """
    Represents a localized group of stationary or severely slow-moving pedestrians.
    """
    def __init__(self, cluster_id: int, member_ids: List[int], center: Tuple[float, float], radius: float, zone: str):
        self.cluster_id = cluster_id
        self.member_ids = member_ids
        self.center = center  # (cx, cy)
        self.radius = radius
        self.zone = zone
        self.severity = "MODERATE" if len(member_ids) < 4 else "HIGH" if len(member_ids) < 7 else "CRITICAL"


class CongestionAnalyzer:
    """
    Analyzes dwell time, stationary clusters, bottleneck formations,
    and calculates continuous Congestion Index for surveillance channels.
    Operates completely in-memory with zero database dependencies.
    """
    def __init__(
        self,
        camera_id: int,
        stationary_speed_threshold: float = 4.0,
        cluster_radius_px: float = 75.0,
        min_cluster_size: int = 3
    ):
        self.camera_id = camera_id
        self.stationary_speed_threshold = stationary_speed_threshold
        self.cluster_radius_px = cluster_radius_px
        self.min_cluster_size = min_cluster_size

        # In-memory tracking state: track_id -> PedestrianState
        self.pedestrians: Dict[int, PedestrianState] = {}

        # Alert state tracking
        self.consecutive_congested_start: Optional[float] = None
        self.active_alert: Optional[Dict[str, Any]] = None

    def analyze_congestion(
        self,
        tracks: List[Dict[str, Any]],
        zones: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processes current frame tracks, updates pedestrian dwell times,
        detects stationary clusters, and calculates Congestion Index.
        """
        now = time.time()
        active_ids = set()

        # Update pedestrian dwell states
        for trk in tracks:
            tid = trk["id"]
            if tid == -1:
                continue
            active_ids.add(tid)
            bbox = trk["bbox"]
            foot_x = (bbox[0] + bbox[2]) / 2.0
            foot_y = float(bbox[3])
            speed = trk.get("movement_speed", 0.0)

            if tid not in self.pedestrians:
                self.pedestrians[tid] = PedestrianState(tid, (foot_x, foot_y), now)
            else:
                self.pedestrians[tid].update((foot_x, foot_y), speed, now, self.stationary_speed_threshold)

            # Attach dwell telemetry directly to track dictionary for annotator
            pstate = self.pedestrians[tid]
            trk["is_stationary"] = pstate.is_stationary
            trk["dwell_time"] = round(pstate.dwell_time, 1)

        # Evict inactive tracks not seen for > 4 seconds
        stale_ids = [tid for tid, p in self.pedestrians.items() if now - p.last_seen > 4.0]
        for tid in stale_ids:
            del self.pedestrians[tid]

        # Gather stationary individuals
        stationary_tracks = [
            trk for trk in tracks
            if trk["id"] in self.pedestrians and self.pedestrians[trk["id"]].is_stationary
        ]
        moving_count = len(tracks) - len(stationary_tracks)

        # Detect spatial clusters among stationary individuals
        clusters = self._detect_clusters(stationary_tracks, zones)

        # Determine bottleneck zones
        bottleneck_zones = list({c.zone for c in clusters if c.zone != "UNKNOWN"})

        # Calculate continuous Congestion Index (0.0 to 1.0)
        total_people = len(tracks)
        if total_people == 0:
            congestion_index = 0.0
            congestion_level = "NORMAL"
        else:
            stationary_ratio = len(stationary_tracks) / float(total_people)
            cluster_factor = min(len(clusters) * 0.25 + sum(len(c.member_ids) for c in clusters) * 0.05, 0.5)
            raw_index = (0.55 * stationary_ratio) + cluster_factor
            congestion_index = min(max(round(raw_index, 2), 0.0), 1.0)

            if congestion_index >= 0.70:
                congestion_level = "SEVERE"
            elif congestion_index >= 0.45:
                congestion_level = "CONGESTED"
            elif congestion_index >= 0.20:
                congestion_level = "MODERATE"
            else:
                congestion_level = "NORMAL"

        # Check for alert condition (CONGESTED or SEVERE for >= 4 seconds)
        self._update_alert_state(congestion_level, congestion_index, bottleneck_zones, len(stationary_tracks), now)

        # Return structured telemetry
        return {
            "congestion_index": congestion_index,
            "congestion_level": congestion_level,
            "total_pedestrians": total_people,
            "stationary_count": len(stationary_tracks),
            "moving_count": moving_count,
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "member_ids": c.member_ids,
                    "center": (round(c.center[0], 1), round(c.center[1], 1)),
                    "radius": round(c.radius, 1),
                    "zone": c.zone,
                    "severity": c.severity
                }
                for c in clusters
            ],
            "bottleneck_zones": bottleneck_zones,
            "active_alert": self.active_alert
        }

    def _detect_clusters(
        self,
        stationary_tracks: List[Dict[str, Any]],
        zones: Optional[Dict[str, Dict[str, Any]]]
    ) -> List[CongestionCluster]:
        """
        Groups stationary individuals within cluster_radius_px using simple distance clustering.
        """
        if len(stationary_tracks) < self.min_cluster_size:
            return []

        points = []
        for trk in stationary_tracks:
            bbox = trk["bbox"]
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = float(bbox[3])
            points.append((trk["id"], cx, cy))

        visited = set()
        clusters = []
        cluster_id_counter = 1

        for i, p1 in enumerate(points):
            tid1, x1, y1 = p1
            if tid1 in visited:
                continue

            # Find all neighbors within radius
            current_cluster_members = [tid1]
            cluster_xs = [x1]
            cluster_ys = [y1]

            for j, p2 in enumerate(points):
                if i == j:
                    continue
                tid2, x2, y2 = p2
                dist = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
                if dist <= self.cluster_radius_px:
                    current_cluster_members.append(tid2)
                    cluster_xs.append(x2)
                    cluster_ys.append(y2)

            if len(current_cluster_members) >= self.min_cluster_size:
                for mid in current_cluster_members:
                    visited.add(mid)

                center_x = sum(cluster_xs) / len(cluster_xs)
                center_y = sum(cluster_ys) / len(cluster_ys)

                # Determine radius covering all members
                max_d = max(
                    math.sqrt((cx - center_x) ** 2 + (cy - center_y) ** 2)
                    for cx, cy in zip(cluster_xs, cluster_ys)
                )
                radius = max(max_d + 20.0, 35.0)

                # Determine which quadrant zone this cluster belongs to
                zone_name = self._find_zone_for_point((center_x, center_y), zones)

                clusters.append(
                    CongestionCluster(
                        cluster_id=cluster_id_counter,
                        member_ids=current_cluster_members,
                        center=(center_x, center_y),
                        radius=radius,
                        zone=zone_name
                    )
                )
                cluster_id_counter += 1

        return clusters

    def _find_zone_for_point(self, point: Tuple[float, float], zones: Optional[Dict[str, Dict[str, Any]]]) -> str:
        if not zones:
            return "UNKNOWN"
        x, y = point
        for zid, zinfo in zones.items():
            px1, py1, px2, py2 = zinfo["pixel_bounds"]
            if px1 <= x <= px2 and py1 <= y <= py2:
                return zinfo.get("name", zid)
        return "UNKNOWN"

    def _update_alert_state(
        self,
        level: str,
        index: float,
        bottlenecks: List[str],
        stationary_count: int,
        timestamp: float
    ):
        """
        Manages transient in-memory congestion alert state.
        """
        is_congested = level in ("CONGESTED", "SEVERE")

        if is_congested:
            if self.consecutive_congested_start is None:
                self.consecutive_congested_start = timestamp

            duration = timestamp - self.consecutive_congested_start
            if duration >= 4.0:
                bottleneck_str = ", ".join(bottlenecks) if bottlenecks else "Main Concourse"
                self.active_alert = {
                    "alert_type": "CONGESTION",
                    "severity": "CRITICAL" if level == "SEVERE" else "HIGH",
                    "level": level,
                    "congestion_index": index,
                    "stationary_count": stationary_count,
                    "bottleneck_location": bottleneck_str,
                    "duration_seconds": round(duration, 1),
                    "message": f"Congestion detected at {bottleneck_str}: {stationary_count} stationary pedestrians (Index: {int(index * 100)}%).",
                    "timestamp": time.strftime("%H:%M:%S")
                }
        else:
            self.consecutive_congested_start = None
            self.active_alert = None
