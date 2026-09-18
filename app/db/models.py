"""Operational schema for fictional users, devices, events, incidents, and audit logs."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    department: Mapped[str] = mapped_column(String(40), nullable=False)
    home_country: Mapped[str] = mapped_column(String(2), nullable=False)
    privileged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('low','medium','high','critical')", name="ck_incident_severity"
        ),
    )

    incident_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    __table_args__ = (
        CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_event_severity"),
        CheckConstraint(
            "failed_attempts IS NULL OR failed_attempts >= 0", name="ck_failed_nonnegative"
        ),
        CheckConstraint(
            "successful_attempts IS NULL OR successful_attempts >= 0", name="ck_success_nonnegative"
        ),
        Index("ix_events_user_timestamp", "user_id", "timestamp"),
        Index("ix_events_timestamp", "timestamp"),
        Index("ix_events_type", "event_type"),
        Index("ix_events_severity", "severity"),
        Index("ix_events_source_ip", "source_ip"),
        Index("ix_events_device", "device_id"),
        Index("ix_events_incident", "incident_id"),
    )

    event_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    source_ip: Mapped[str] = mapped_column(String(45), nullable=False)
    destination_ip: Mapped[str | None] = mapped_column(String(45))
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.device_id"))
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    country: Mapped[str | None] = mapped_column(String(2))
    authentication_method: Mapped[str | None] = mapped_column(String(24))
    failed_attempts: Mapped[int | None] = mapped_column(Integer)
    successful_attempts: Mapped[int | None] = mapped_column(Integer)
    privileged_account: Mapped[bool | None] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.incident_id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"))
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(40))
    result: Mapped[str] = mapped_column(String(24), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
