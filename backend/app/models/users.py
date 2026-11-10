from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    func,
    text,
)

from app.core.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'employee')", name="users_role_check"),
        CheckConstraint("login ~ '^[a-z0-9._-]{3,64}$'", name="users_login_check"),
    )

    id = Column(Integer, primary_key=True)
    login = Column(String(64), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(16), nullable=False, server_default="employee")
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    token_version = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    key = Column(String(64), primary_key=True)
    count = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
