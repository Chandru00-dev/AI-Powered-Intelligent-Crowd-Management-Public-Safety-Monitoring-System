import cv2
import numpy as np
from typing import List, Dict, Any, Optional


def annotate_frame(
    frame: np.ndarray,
    tracks: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    fps: float = 0.0,
    zones: Optional[Dict[str, Dict[str, Any]]] = None,
    congestion: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Renders bounding boxes, motion tracking trails, zone boundaries,
    congestion/bottleneck clusters, stationary target indicators,
    and a real-time telemetry HUD overlay directly onto the video frame.
    """
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    # 1. Draw Phase 4 Spatial Zones if configured
    if zones:
        # Crosshair quadrant lines
        mid_x, mid_y = w // 2, h // 2
        cv2.line(annotated, (mid_x, 36), (mid_x, h), (70, 80, 95), 1, cv2.LINE_AA)
        cv2.line(annotated, (0, mid_y), (w, mid_y), (70, 80, 95), 1, cv2.LINE_AA)

        for zid, zinfo in zones.items():
            x1, y1, x2, y2 = zinfo["pixel_bounds"]
            cnt = zinfo["people_count"]
            level = zinfo["density_level"]
            zname = zinfo["name"].split(":")[0]  # e.g. "Zone A"

            # Color by density
            if level == "CRITICAL":
                border_color = (68, 68, 239)    # Red
            elif level == "HIGH":
                border_color = (22, 115, 249)   # Orange
            elif level == "MEDIUM":
                border_color = (11, 158, 245)   # Amber
            else:
                border_color = (129, 185, 16)   # Green

            # Subtle corner boundary for each zone
            cv2.rectangle(annotated, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), (45, 55, 72), 1)

            # Zone badge banner
            badge_text = f"{zname} | {cnt} PPL ({level})"
            (bw, bh), _ = cv2.getTextSize(badge_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)

            bx1 = x1 + 10
            by1 = max(y1 + 10, 42)
            cv2.rectangle(annotated, (bx1, by1), (bx1 + bw + 12, by1 + bh + 8), (17, 24, 39), -1)
            cv2.rectangle(annotated, (bx1, by1), (bx1 + bw + 12, by1 + bh + 8), border_color, 1)
            cv2.putText(annotated, badge_text, (bx1 + 6, by1 + bh + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, border_color, 1, cv2.LINE_AA)

    # 2. Draw Phase 5 Congestion Clusters & Bottlenecks
    if congestion and "clusters" in congestion:
        for c in congestion["clusters"]:
            cx, cy = int(c["center"][0]), int(c["center"][1])
            cr = int(c["radius"])
            sev = c.get("severity", "MODERATE")
            cluster_color = (68, 68, 239) if sev == "CRITICAL" else (22, 115, 249) if sev == "HIGH" else (11, 158, 245)

            # Draw outer warning halo
            cv2.circle(annotated, (cx, cy), cr, cluster_color, 2, cv2.LINE_AA)
            cv2.circle(annotated, (cx, cy), cr + 4, (30, 30, 40), 1, cv2.LINE_AA)

            # Cluster badge
            c_text = f"BOTTLENECK ({len(c['member_ids'])} PPL)"
            (cw, ch), _ = cv2.getTextSize(c_text, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
            cv2.rectangle(annotated, (cx - cw // 2 - 4, cy - cr - ch - 6), (cx + cw // 2 + 4, cy - cr), (17, 24, 39), -1)
            cv2.rectangle(annotated, (cx - cw // 2 - 4, cy - cr - ch - 6), (cx + cw // 2 + 4, cy - cr), cluster_color, 1)
            cv2.putText(annotated, c_text, (cx - cw // 2, cy - cr - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Draw tracks, bounding boxes, motion trails, and stationary badges
    for trk in tracks:
        x1, y1, x2, y2 = trk["bbox"]
        track_id = trk["id"]
        conf = trk["confidence"]
        speed = trk.get("movement_speed", 0.0)
        is_stationary = trk.get("is_stationary", False)
        dwell_time = trk.get("dwell_time", 0.0)

        # Highlight stationary/congested individuals in Amber or Red
        if is_stationary:
            color = (68, 68, 239) if dwell_time > 10.0 else (22, 115, 249)
        else:
            color = (212, 182, 6)  # Default Cyan (BGR)

        # Draw main bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        # Draw corner brackets for surveillance look
        corner_len = min(15, (x2 - x1) // 4, (y2 - y1) // 4)
        if corner_len > 3:
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), (255, 255, 255), 2)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), (255, 255, 255), 2)
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), (255, 255, 255), 2)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), (255, 255, 255), 2)
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), (255, 255, 255), 2)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), (255, 255, 255), 2)
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), (255, 255, 255), 2)
            cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), (255, 255, 255), 2)

        # Draw motion trail
        history = trk.get("history", [])
        if len(history) > 1 and not is_stationary:
            pts = np.array(history, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts], False, (0, 220, 255), 1, cv2.LINE_AA)

        # Label badge
        id_str = f"ID #{track_id}" if track_id != -1 else "PERSON"
        if is_stationary:
            label_text = f"{id_str} [STOPPED {int(dwell_time)}s]"
        else:
            label_text = f"{id_str} {int(conf * 100)}%"

        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        badge_y = max(y1 - 6, th + 6)
        cv2.rectangle(annotated, (x1, badge_y - th - 4), (x1 + tw + 8, badge_y + 2), (20, 24, 32), -1)
        cv2.rectangle(annotated, (x1, badge_y - th - 4), (x1 + tw + 8, badge_y + 2), color, 1)
        cv2.putText(annotated, label_text, (x1 + 4, badge_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1)

    # 4. Top HUD Bar
    hud_overlay = annotated.copy()
    cv2.rectangle(hud_overlay, (0, 0), (w, 36), (11, 15, 25), -1)
    cv2.addWeighted(hud_overlay, 0.75, annotated, 0.25, 0, annotated)

    # HUD Telemetry Text
    current_cnt = metrics.get("current_people", 0)
    peak_cnt = metrics.get("peak_people", 0)
    fps_str = f"{fps:.1f} FPS" if fps > 0 else "25.0 FPS"

    hud_str = f"AI SURVEILLANCE  |  HEADCOUNT: {current_cnt}  |  PEAK: {peak_cnt}  |  {fps_str}"

    if congestion:
        c_level = congestion.get("congestion_level", "NORMAL")
        c_idx = int(congestion.get("congestion_index", 0.0) * 100)
        hud_str += f"  |  CONGESTION: {c_level} ({c_idx}%)"
        bn = congestion.get("bottleneck_zones", [])
        if bn:
            short_bn = bn[0].split(":")[0]
            hud_str += f"  |  BOTTLENECK: {short_bn}"

    cv2.putText(annotated, hud_str, (12, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 225, 255), 1, cv2.LINE_AA)

    return annotated
