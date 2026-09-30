import os
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any, Generator
import cv2
import numpy as np
from backend.app.core.config import settings
from backend.app.models.camera import CameraInputType, CameraStatus

logger = logging.getLogger("crowd_safety.video")

class VideoSource(ABC):
    """
    Abstract Base Class for Video Sources (Files, Webcams, RTSP streams).
    Decoupled from API routes and streaming logic.
    """
    def __init__(self, source: str, name: str = "Camera"):
        self.source = source
        self.name = name
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_connected: bool = False
        self.lock = threading.Lock()
        self.last_frame_time: float = 0.0

    @abstractmethod
    def connect(self) -> bool:
        """Initialize connection to the video source."""
        pass

    @abstractmethod
    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read a single frame from the video source."""
        pass

    def disconnect(self) -> None:
        """Safely release the capture object."""
        with self.lock:
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception as e:
                    logger.error(f"Error releasing video capture for {self.name}: {e}")
                finally:
                    self.cap = None
            self.is_connected = False
            logger.info(f"Disconnected video source: {self.name}")

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Probe connection, return (success, message, metadata)."""
        start_time = time.time()
        connected = self.connect()
        latency = round((time.time() - start_time) * 1000, 1)

        if not connected or self.cap is None or not self.cap.isOpened():
            self.disconnect()
            return False, "Unable to establish connection to the video source.", {"latency_ms": latency}

        success, frame = self.read_frame()
        if not success or frame is None:
            self.disconnect()
            return False, "Connected but failed to read video frame. Stream may be inactive or empty.", {"latency_ms": latency}

        height, width = frame.shape[:2]
        raw_fps = self.cap.get(cv2.CAP_PROP_FPS) if self.cap else 25.0
        fps = round(raw_fps, 1) if (raw_fps is not None and raw_fps > 0) else 25.0
        meta = {
            "resolution": f"{width}x{height}",
            "fps": fps,
            "latency_ms": latency,
            "channels": frame.shape[2] if len(frame.shape) > 2 else 1
        }
        self.disconnect()
        return True, "Camera connection verified successfully.", meta


class VideoFileSource(VideoSource):
    """Handles local video files (e.g., sample_crowd.mp4) with continuous looping."""
    def __init__(self, source: str, name: str = "Video File"):
        # If path is relative, resolve from project root
        resolved = source
        if not os.path.isabs(source):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            alt_path = os.path.join(project_root, source)
            if os.path.exists(alt_path):
                resolved = alt_path
        super().__init__(resolved, name)

    def connect(self) -> bool:
        with self.lock:
            if not os.path.exists(self.source):
                logger.warning(f"Video file not found at path: {self.source}")
                return False
            self.cap = cv2.VideoCapture(self.source)
            self.is_connected = self.cap.isOpened()
            return self.is_connected


    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                if not self.connect():
                    return False, None

            ret, frame = self.cap.read()
            if not ret or frame is None:
                # Loop video file back to beginning for continuous demo monitoring
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()

            if ret and frame is not None:
                self.last_frame_time = time.time()
                return True, frame
            return False, None


class WebcamSource(VideoSource):
    """
    Handles USB / integrated laptop webcams via device index with
    multi-backend fallback (DirectShow -> Media Foundation -> Default).
    """
    def __init__(self, source: str, name: str = "Webcam"):
        super().__init__(source, name)
        # Parse device index robustly: extract digits if available, default to 0
        clean_digits = "".join(filter(str.isdigit, str(source)))
        try:
            self.device_index = int(clean_digits) if clean_digits else 0
        except ValueError:
            self.device_index = 0

    def connect(self) -> bool:
        with self.lock:
            if self.cap is not None and self.cap.isOpened():
                return True

            # Backends to try in order of performance on Windows
            if os.name == 'nt':
                backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            else:
                backends = [cv2.CAP_ANY]

            # 1. Try configured device index across backends
            for backend in backends:
                try:
                    cap = cv2.VideoCapture(self.device_index, backend)
                    if cap.isOpened():
                        # Read quick frame to verify sensor stream is active
                        ret, test_frame = cap.read()
                        if ret and test_frame is not None:
                            self.cap = cap
                            self.is_connected = True
                            logger.info(f"Webcam opened at index {self.device_index} using backend {backend}")
                            return True
                    cap.release()
                except Exception as e:
                    logger.debug(f"Webcam backend {backend} failed for index {self.device_index}: {e}")

            # 2. If user configured index != 0 and it failed, auto-fallback to index 0
            if self.device_index != 0:
                logger.info(f"Index {self.device_index} failed; attempting fallback to default webcam index 0")
                for backend in backends:
                    try:
                        cap = cv2.VideoCapture(0, backend)
                        if cap.isOpened():
                            ret, test_frame = cap.read()
                            if ret and test_frame is not None:
                                self.device_index = 0
                                self.cap = cap
                                self.is_connected = True
                                logger.info(f"Webcam opened on fallback index 0 using backend {backend}")
                                return True
                        cap.release()
                    except Exception:
                        pass

            self.is_connected = False
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                if not self.connect():
                    return False, None

            ret, frame = self.cap.read()
            if not ret or frame is None:
                # Retry once to handle frame drops
                time.sleep(0.01)
                ret, frame = self.cap.read()

            if ret and frame is not None:
                self.last_frame_time = time.time()
                return True, frame

            # If frames completely stop, disconnect to allow fresh reconnection
            self.disconnect()
            return False, None



class RTSPSource(VideoSource):
    """
    Handles IP CCTV RTSP streams with timeouts, error handling,
    and credential security.
    """
    def __init__(self, source: str, name: str = "RTSP Camera", username: str = None, password: str = None):
        super().__init__(source, name)
        self.username = username
        self.password = password
        self._sanitized_source = self._sanitize_url(source)

    def _get_authenticated_url(self) -> str:
        """Inject credentials securely if provided separately."""
        if self.username and self.password and "@" not in self.source:
            if self.source.startswith("rtsp://"):
                clean = self.source[7:]
                return f"rtsp://{self.username}:{self.password}@{clean}"
        return self.source

    def _sanitize_url(self, url: str) -> str:
        """Strip password from RTSP URL for safe logging and client exposure."""
        try:
            if "@" in url and "://" in url:
                protocol, rest = url.split("://", 1)
                creds, host_path = rest.split("@", 1)
                user = creds.split(":")[0] if ":" in creds else creds
                return f"{protocol}://{user}:****@{host_path}"
        except Exception:
            pass
        return url

    def connect(self) -> bool:
        with self.lock:
            stream_url = self._get_authenticated_url()
            # Set transport and timeouts in OpenCV / FFMPEG environment
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                f"rtsp_transport;tcp|stimeout;{settings.RTSP_TIMEOUT_MS * 1000}"
            )
            self.cap = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
            self.is_connected = self.cap.isOpened()
            if not self.is_connected:
                logger.warning(f"Unable to connect to RTSP stream: {self._sanitized_source}")
            return self.is_connected

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.cap is None or not self.cap.isOpened():
                if not self.connect():
                    return False, None
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.last_frame_time = time.time()
                return True, frame
            return False, None


def create_video_source(input_type: CameraInputType, source: str, name: str = "Camera", username: str = None, password: str = None) -> VideoSource:
    """Factory method to instantiate appropriate VideoSource."""
    if input_type == CameraInputType.VIDEO_FILE:
        return VideoFileSource(source=source, name=name)
    elif input_type == CameraInputType.WEBCAM:
        return WebcamSource(source=source, name=name)
    elif input_type == CameraInputType.RTSP:
        return RTSPSource(source=source, name=name, username=username, password=password)
    else:
        raise ValueError(f"Unsupported camera input type: {input_type}")


def generate_status_frame(camera_name: str, status_text: str, sub_text: str = "") -> np.ndarray:
    """
    Renders an elegant security HUD status card directly onto an image buffer
    when a camera is offline or connecting.
    """
    width, height = 640, 360
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Dark slate background with grid lines
    frame[:] = (15, 23, 42)  # #0f172a
    for x in range(0, width, 40):
        cv2.line(frame, (x, 0), (x, height), (30, 41, 59), 1)
    for y in range(0, height, 40):
        cv2.line(frame, (0, y), (width, y), (30, 41, 59), 1)

    # Frame border
    cv2.rectangle(frame, (10, 10), (width - 10, height - 10), (51, 65, 85), 1)

    # Header badge
    cv2.rectangle(frame, (20, 20), (width - 20, 60), (30, 41, 59), -1)
    cv2.putText(frame, f"CAM: {camera_name.upper()}", (30, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 1)

    # Status text
    is_offline = "OFFLINE" in status_text.upper() or "ERROR" in status_text.upper()
    color = (80, 80, 239) if is_offline else (234, 179, 8)  # Red or Amber in BGR
    cv2.putText(frame, f"STATUS: {status_text}", (30, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if sub_text:
        cv2.putText(frame, sub_text, (30, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1)

    # Timestamp
    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC")
    cv2.putText(frame, now_str, (30, height - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 116, 139), 1)

    return frame
