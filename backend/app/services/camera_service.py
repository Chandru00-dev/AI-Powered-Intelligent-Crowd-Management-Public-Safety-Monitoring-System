import asyncio
import time
import logging
from typing import Dict, Optional, Tuple, Any, Generator
import cv2
from sqlalchemy.orm import Session
from backend.app.models.camera import Camera, CameraStatus, CameraInputType
from backend.app.schemas.camera import CameraCreate, CameraUpdate
from backend.app.services.video_source import (
    VideoSource,
    create_video_source,
    generate_status_frame
)
from backend.app.core.config import settings

logger = logging.getLogger("crowd_safety.camera_service")

class CameraService:
    def __init__(self):
        # Keep track of active video sources: camera_id -> VideoSource
        self._active_sources: Dict[int, VideoSource] = {}

    def get_or_create_source(self, camera: Camera) -> VideoSource:
        if camera.id in self._active_sources:
            return self._active_sources[camera.id]

        source = create_video_source(
            input_type=camera.input_type,
            source=camera.source,
            name=camera.name,
            username=camera.username,
            password=camera.password_encrypted
        )
        self._active_sources[camera.id] = source
        return source

    def release_source(self, camera_id: int) -> None:
        if camera_id in self._active_sources:
            try:
                self._active_sources[camera_id].disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting camera {camera_id}: {e}")
            finally:
                del self._active_sources[camera_id]

    def test_camera(self, camera: Camera) -> Tuple[bool, CameraStatus, str, Dict[str, Any]]:
        """Tests connection for an existing camera in DB."""
        source = create_video_source(
            input_type=camera.input_type,
            source=camera.source,
            name=camera.name,
            username=camera.username,
            password=camera.password_encrypted
        )
        success, message, meta = source.test_connection()
        status = CameraStatus.ONLINE if success else CameraStatus.OFFLINE
        return success, status, message, meta

    def test_raw_source(self, input_type: CameraInputType, source_path: str, username: Optional[str] = None, password: Optional[str] = None) -> Tuple[bool, CameraStatus, str, Dict[str, Any]]:
        """Tests connection for a new candidate camera configuration."""
        source = create_video_source(
            input_type=input_type,
            source=source_path,
            name="Test Source",
            username=username,
            password=password
        )
        success, message, meta = source.test_connection()
        status = CameraStatus.ONLINE if success else CameraStatus.OFFLINE
        return success, status, message, meta

    async def stream_mjpeg(self, camera_id: int, db: Session, annotate: bool = True, heatmap: bool = False):
        """
        Asynchronous generator yielding multipart/x-mixed-replace MJPEG bytes.
        Non-blocking: uses asyncio.sleep to yield execution back to FastAPI event loop.
        """
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            # Yield not found frame
            err_frame = generate_status_frame("Unknown", "CAMERA NOT FOUND", "ID does not exist in registry")
            _, jpeg = cv2.imencode(".jpg", err_frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
            return

        if not camera.enabled or camera.status == CameraStatus.DISABLED:
            err_frame = generate_status_frame(camera.name, "CAMERA DISABLED", "Camera is disabled in administration")
            _, jpeg = cv2.imencode(".jpg", err_frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
            return

        video_source = self.get_or_create_source(camera)
        connected = video_source.connect()
        if not connected:
            camera.status = CameraStatus.OFFLINE
            db.commit()
            err_frame = generate_status_frame(
                camera.name,
                "CAMERA OFFLINE",
                "Unable to connect to video feed. Check stream path/credentials."
            )
            _, jpeg = cv2.imencode(".jpg", err_frame)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
            return

        # Update status to ONLINE
        camera.status = CameraStatus.ONLINE
        db.commit()

        frame_interval = 1.0 / max(settings.MAX_STREAM_FPS, 1)

        try:
            while True:
                start_cycle = time.time()
                success, frame = video_source.read_frame()

                if not success or frame is None:
                    # Camera dropped or stream interrupted
                    err_frame = generate_status_frame(
                        camera.name,
                        "STREAM RECONNECTING",
                        "Attempting to re-acquire video frames..."
                    )
                    _, jpeg = cv2.imencode(".jpg", err_frame, [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY])
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                    await asyncio.sleep(1.0)
                    continue

                # Run Phase 3 YOLO Detection & Phase 4 Density Analysis
                try:
                    from backend.ai.pipeline import ai_pipeline
                    processed_frame, metrics = ai_pipeline.process_camera_frame(
                        camera_id=camera_id,
                        frame=frame,
                        db=db,
                        annotate=annotate,
                        heatmap=heatmap
                    )
                except Exception as e:
                    logger.error(f"AI inference error for camera {camera_id}: {e}")
                    processed_frame = frame



                # Encode frame to JPEG
                ret, buffer = cv2.imencode(".jpg", processed_frame, [cv2.IMWRITE_JPEG_QUALITY, settings.JPEG_QUALITY])
                if not ret:
                    await asyncio.sleep(0.05)
                    continue

                frame_bytes = buffer.tobytes()
                yield (

                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n" +
                    frame_bytes + b"\r\n"
                )

                # Regulate frame rate and yield control
                elapsed = time.time() - start_cycle
                sleep_time = max(0.001, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            logger.info(f"Client disconnected from stream: Camera {camera_id}")
        except Exception as e:
            logger.error(f"Error in stream_mjpeg for Camera {camera_id}: {e}")
        finally:
            logger.debug(f"Stream consumer ended for Camera {camera_id}")

camera_service = CameraService()
