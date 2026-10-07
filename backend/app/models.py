from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    admin = "admin"
    collector = "collector"
    plant = "plant"
    supervisor = "supervisor"


class WasteColor(str, Enum):
    amarillo = "amarillo"
    verde = "verde"
    azul = "azul"


class ScanStage(str, Enum):
    pickup = "pickup"
    plant = "plant"


class TripStatus(str, Enum):
    open = "open"
    arrived = "arrived"
    closed = "closed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    tax_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    site_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    labels: Mapped[list[QrLabel]] = relationship(back_populates="company", cascade="all, delete-orphan")


class QrLabel(Base):
    __tablename__ = "qr_labels"
    __table_args__ = (UniqueConstraint("company_id", "color", name="uq_company_color"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    color: Mapped[WasteColor] = mapped_column(SAEnum(WasteColor), index=True)
    material_name: Mapped[str] = mapped_column(String(120))
    public_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company] = relationship(back_populates="labels")


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    vehicle: Mapped[str] = mapped_column(String(80))
    collector_name: Mapped[str] = mapped_column(String(160))
    status: Mapped[TripStatus] = mapped_column(SAEnum(TripStatus), default=TripStatus.open, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scans: Mapped[list[ScanEvent]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    weighings: Mapped[list[Weighing]] = relationship(back_populates="trip", cascade="all, delete-orphan")


class ScanEvent(Base):
    __tablename__ = "scan_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    qr_label_id: Mapped[int] = mapped_column(ForeignKey("qr_labels.id"), index=True)
    stage: Mapped[ScanStage] = mapped_column(SAEnum(ScanStage), index=True)
    client_event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    scanned_by: Mapped[str] = mapped_column(String(160))
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    trip: Mapped[Trip] = relationship(back_populates="scans")
    label: Mapped[QrLabel] = relationship()


class Weighing(Base):
    __tablename__ = "weighings"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    qr_label_id: Mapped[int] = mapped_column(ForeignKey("qr_labels.id"), index=True)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    client_event_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    weighed_by: Mapped[str] = mapped_column(String(160))
    weighed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    trip: Mapped[Trip] = relationship(back_populates="weighings")
    label: Mapped[QrLabel] = relationship()
