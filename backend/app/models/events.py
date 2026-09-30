import enum
from sqlalchemy import Column, String, Integer, Float, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class AlertType(str, enum.Enum):
    HIGH_CROWD = "HIGH_CROWD"
    CONGESTION = "CONGESTION"
    FIRE = "FIRE"
    SMOKE = "SMOKE"
    SUSPICIOUS_OBJECT = "SUSPICIOUS_OBJECT"
    ABANDONED_OBJECT = "ABANDONED_OBJECT"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    SYSTEM_ERROR = "SYSTEM_ERROR"

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"

class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=True)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.MEDIUM, nullable=False, index=True)
    message = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False, index=True)
    reviewed_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)

class DetectionEvent(Base, TimestampMixin):
    __tablename__ = "detection_events"

    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    details = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)

class CrowdMetric(Base, TimestampMixin):
    __tablename__ = "crowd_metrics"

    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    people_count = Column(Integer, default=0, nullable=False)
    density_level = Column(String(20), default="LOW", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    movement_speed = Column(Float, default=0.0)

class ZoneMetric(Base, TimestampMixin):
    __tablename__ = "zone_metrics"

    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    zone_name = Column(String(50), nullable=False)
    people_count = Column(Integer, default=0, nullable=False)
    density_level = Column(String(20), default="LOW", nullable=False)
