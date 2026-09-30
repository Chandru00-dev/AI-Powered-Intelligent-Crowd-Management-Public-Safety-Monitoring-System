import enum
from sqlalchemy import Column, String, Boolean, Enum
from backend.app.core.database import Base
from backend.app.models.base import TimestampMixin

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SECURITY_OPERATOR = "SECURITY_OPERATOR"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.SECURITY_OPERATOR, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
