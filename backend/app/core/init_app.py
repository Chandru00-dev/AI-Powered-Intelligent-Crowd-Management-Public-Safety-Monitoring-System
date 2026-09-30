import os
import math
import logging
import cv2
import numpy as np
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, init_db
from backend.app.core.security import hash_password
from backend.app.models.user import User, UserRole
from backend.app.models.camera import Camera, CameraInputType, CameraStatus
from backend.app.models.events import Alert, AlertType, AlertSeverity, AlertStatus

logger = logging.getLogger("crowd_safety.init")

def create_sample_video_if_missing(video_path: str) -> str:
    """
    Synthesizes a realistic simulated CCTV crowd monitoring MP4 clip
    if no physical video file is already present. This ensures 100% out-of-the-box
    functionality without requiring external downloads or hardware cameras.
    """
    os.makedirs(os.path.dirname(os.path.abspath(video_path)), exist_ok=True)
    if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
        return video_path

    logger.info(f"Generating synthetic sample CCTV video at {video_path}...")
    width, height = 640, 360
    fps = 20
    duration_sec = 6  # 120 frames total loop
    total_frames = fps * duration_sec

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    # Initialize 18 simulated walking pedestrian agents
    np.random.seed(42)
    agents = []
    for i in range(18):
        agents.append({
            "x": float(np.random.randint(60, width - 60)),
            "y": float(np.random.randint(80, height - 60)),
            "vx": float(np.random.uniform(-1.8, 1.8)),
            "vy": float(np.random.uniform(-1.2, 1.2)),
            "color": (int(np.random.randint(180, 240)), int(np.random.randint(140, 210)), int(np.random.randint(90, 150))),
            "radius": int(np.random.randint(8, 12))
        })

    for frame_idx in range(total_frames):
        # CCTV surveillance background: Dark pavement with lane markings and security HUD
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (35, 38, 44)  # slate asphalt

        # Hallway / Plaza perspective lines
        cv2.line(frame, (100, 0), (0, height), (55, 60, 70), 2)
        cv2.line(frame, (width - 100, 0), (width, height), (55, 60, 70), 2)
        cv2.line(frame, (220, 0), (180, height), (50, 55, 65), 1)
        cv2.line(frame, (width - 220, 0), (width - 180, height), (50, 55, 65), 1)

        # Entrance doorway zone outline
        cv2.rectangle(frame, (230, 40), (410, 140), (70, 80, 95), 1)
        cv2.putText(frame, "ZONE A: MAIN PLAZA", (240, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 140, 160), 1)

        # Update and render agents
        for ag in agents:
            ag["x"] += ag["vx"]
            ag["y"] += ag["vy"]

            # Bounce off walls
            if ag["x"] < 50 or ag["x"] > width - 50:
                ag["vx"] *= -1
            if ag["y"] < 70 or ag["y"] > height - 40:
                ag["vy"] *= -1

            x_int, y_int = int(ag["x"]), int(ag["y"])
            r = ag["radius"]

            # Draw person figure (head + body)
            cv2.circle(frame, (x_int, y_int - r - 4), int(r * 0.7), (210, 225, 240), -1)  # Head
            cv2.ellipse(frame, (x_int, y_int), (r, int(r * 1.5)), 0, 0, 360, ag["color"], -1)  # Body
            # Simulated shadow
            cv2.ellipse(frame, (x_int, y_int + int(r * 1.5)), (r + 2, 4), 0, 0, 360, (20, 22, 26), -1)

        # CCTV timestamp and camera identifier overlay
        cv2.rectangle(frame, (10, 10), (280, 34), (20, 24, 30), -1)
        cv2.putText(frame, "CAM-01 [MAIN ENTRANCE GATE]", (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 220, 255), 1)

        timestamp_str = f"2026-09-04 08:30:{frame_idx // fps:02d}.{frame_idx % fps * 50:03d} REC [LIVE]"
        cv2.rectangle(frame, (10, height - 28), (340, height - 8), (20, 24, 30), -1)
        cv2.putText(frame, timestamp_str, (16, height - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 220, 200), 1)

        out.write(frame)

    out.release()
    logger.info(f"Sample video generated ({total_frames} frames).")
    return video_path

def initialize_system():
    """Initializes DB schemas, default admin & operator, sample video, and default camera."""
    init_db()
    db: Session = SessionLocal()

    try:
        # 1. Ensure Default Admin Account
        admin_user = db.query(User).filter(User.email == settings.DEFAULT_ADMIN_EMAIL).first()
        if not admin_user:
            logger.info(f"Creating default admin account: {settings.DEFAULT_ADMIN_EMAIL}")
            admin_user = User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                username="admin",
                full_name=settings.DEFAULT_ADMIN_NAME,
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)

        # 2. Ensure Default Security Operator Account
        operator_user = db.query(User).filter(User.email == settings.DEFAULT_OPERATOR_EMAIL).first()
        if not operator_user:
            logger.info(f"Creating default operator account: {settings.DEFAULT_OPERATOR_EMAIL}")
            operator_user = User(
                email=settings.DEFAULT_OPERATOR_EMAIL,
                username="operator",
                full_name=settings.DEFAULT_OPERATOR_NAME,
                hashed_password=hash_password(settings.DEFAULT_OPERATOR_PASSWORD),
                role=UserRole.SECURITY_OPERATOR,
                is_active=True
            )
            db.add(operator_user)

        db.commit()

        # 3. Setup Sample Video Asset
        # init_app.py is in backend/app/core -> 4 dirnames up is workspace root
        core_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(core_dir)
        backend_dir = os.path.dirname(app_dir)
        project_root = os.path.dirname(backend_dir)
        sample_video_path = os.path.join(project_root, "frontend", "assets", "samples", "sample_crowd.mp4")
        create_sample_video_if_missing(sample_video_path)

        # 4. Ensure Initial Demo Camera
        sample_cam = db.query(Camera).filter(Camera.name == "Main Entrance CCTV").first()
        if not sample_cam:
            logger.info("Registering default sample CCTV camera in database...")
            sample_cam = Camera(
                name="Main Entrance CCTV",
                location="Main Entrance Plaza",
                input_type=CameraInputType.VIDEO_FILE,
                source=sample_video_path,
                status=CameraStatus.ONLINE,
                enabled=True,
                resolution="640x360",
                fps=20.0,
                description="Simulated surveillance camera monitoring pedestrian influx at main entrance plaza."
            )
            db.add(sample_cam)
            db.commit()
            db.refresh(sample_cam)
        else:
            # Normalize existing camera path if needed
            if not os.path.exists(sample_cam.source) and os.path.exists(sample_video_path):
                sample_cam.source = sample_video_path
                db.commit()


        # 5. Ensure Initial Sample Alerts for Dashboard Demo
        alert_count = db.query(Alert).count()
        if alert_count == 0:
            demo_alerts = [
                Alert(
                    camera_id=sample_cam.id if sample_cam else None,
                    alert_type=AlertType.HIGH_CROWD,
                    severity=AlertSeverity.HIGH,
                    message="Crowd density approaching threshold limit in Main Entrance Plaza (Zone A).",
                    confidence=0.92,
                    status=AlertStatus.ACTIVE
                ),
                Alert(
                    camera_id=sample_cam.id if sample_cam else None,
                    alert_type=AlertType.CAMERA_OFFLINE,
                    severity=AlertSeverity.LOW,
                    message="Periodic connection latency spike detected on auxiliary RTSP node.",
                    confidence=1.0,
                    status=AlertStatus.REVIEWED
                )
            ]
            db.add_all(demo_alerts)
            db.commit()

        logger.info("System initialization complete.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during system initialization: {e}")
    finally:
        db.close()
