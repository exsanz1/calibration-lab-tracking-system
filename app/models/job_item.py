from __future__ import annotations

import enum

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Scope(str, enum.Enum):
    PRESSURE = "PRESSURE"
    FORCE = "FORCE"
    TEMP = "TEMP"
    MASS = "MASS"
    DIMENSION = "DIMENSION"
    OTHER = "OTHER"


class JobStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    QUEUED = "QUEUED"
    CALIBRATING = "CALIBRATING"
    REVIEW = "REVIEW"
    CERT_READY = "CERT_READY"
    HOLD_ADMIN = "HOLD_ADMIN"
    DELIVERED = "DELIVERED"


class JobItem(Base):
    __tablename__ = "job_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    qr_tag: Mapped[str] = mapped_column(String(50), unique=True)
    instrument_name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(100), default=None)
    model: Mapped[str | None] = mapped_column(String(100), default=None)
    serial_number: Mapped[str] = mapped_column(String(100))
    scope: Mapped[Scope] = mapped_column()
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.RECEIVED)
    assigned_tech: Mapped[str | None] = mapped_column(String(100), default=None)
    worksheet_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    certificate_no: Mapped[str | None] = mapped_column(String(50), default=None)
    certificate_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    release_allowed: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped[Order] = relationship(back_populates="job_items")
