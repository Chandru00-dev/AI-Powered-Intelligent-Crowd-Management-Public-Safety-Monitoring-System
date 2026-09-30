from sqlalchemy import Column, String, Text
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), default="GENERAL", nullable=False)

    def __repr__(self):
        return f"<SystemSetting {self.key}={self.value}>"
