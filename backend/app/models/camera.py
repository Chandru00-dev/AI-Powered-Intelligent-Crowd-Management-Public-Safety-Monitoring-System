import enum
from sqlalchemy import Column, String, Boolean, Enum, Float, Text
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class CameraInputType(str, enum.Enum):
    VIDEO_FILE = "VIDEO_FILE"
    WEBCAM = "WEBCAM"
    RTSP = "RTSP"

class CameraStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"
    ERROR = "ERROR"
    DISABLED = "DISABLED"

class Camera(Base, TimestampMixin):
    __tablename__ = "cameras"

    name = Column(String(150), nullable=False, index=True)
    location = Column(String(200), nullable=False)
    input_type = Column(Enum(CameraInputType), nullable=False)
    source = Column(Text, nullable=False)  # Path, device index, or RTSP URL
    username = Column(String(100), nullable=True)
    password_encrypted = Column(String(255), nullable=True)
    status = Column(Enum(CameraStatus), default=CameraStatus.OFFLINE, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    resolution = Column(String(50), nullable=True, default="N/A")
    fps = Column(Float, nullable=True, default=0.0)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Camera {self.name} ({self.input_type}) - {self.status}>"
