from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.master_equipment import MasterEquipment
    from app.models.order import Order


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
    accessories: Mapped[str | None] = mapped_column(String(200), default="Unit Only")
    intake_condition: Mapped[str] = mapped_column(String(50), default="GOOD")
    master_equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("master_equipments.id"), default=None, nullable=True
    )
    worksheet_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    certificate_no: Mapped[str | None] = mapped_column(String(50), default=None)
    certificate_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    release_allowed: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped[Order] = relationship("Order", back_populates="job_items")
    master_equipment: Mapped[MasterEquipment | None] = relationship("MasterEquipment")
