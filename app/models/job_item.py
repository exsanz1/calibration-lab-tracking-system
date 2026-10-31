from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.master_equipment import MasterEquipment
    from app.models.order import Order
    from app.models.po_out import PurchaseOrderOut
    from app.models.subcontractor import Subcontractor


class Scope(str, enum.Enum):
    PRESSURE = "PRESSURE"
    FORCE = "FORCE"
    TEMP = "TEMP"
    MASS = "MASS"
    DIMENSION = "DIMENSION"
    OTHER = "OTHER"


class JobStatus(str, enum.Enum):
    ORDERED = "ORDERED"
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
    specification_desc: Mapped[str | None] = mapped_column(String(500), default=None)
    brand: Mapped[str | None] = mapped_column(String(100), default=None)
    model: Mapped[str | None] = mapped_column(String(100), default=None)
    serial_number: Mapped[str] = mapped_column(String(100))
    scope: Mapped[Scope] = mapped_column()

    # Commercial & Subcontractor attributes
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit: Mapped[str] = mapped_column(String(50), default="Unit")
    unit_price: Mapped[int] = mapped_column(Integer, default=0)
    subcontractor_id: Mapped[int | None] = mapped_column(
        ForeignKey("subcontractors.id"), default=None, nullable=True
    )
    subcon_price: Mapped[int] = mapped_column(Integer, default=0)
    po_out_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_orders_out.id"), default=None, nullable=True
    )

    # Technical pipeline status
    status: Mapped[JobStatus] = mapped_column(default=JobStatus.RECEIVED)
    assigned_tech: Mapped[str | None] = mapped_column(String(100), default=None)
    accessories: Mapped[str | None] = mapped_column(String(200), default="Unit Only")
    intake_condition: Mapped[str] = mapped_column(String(50), default="GOOD")

    # Traceability & Certificate
    master_equipment_id: Mapped[int | None] = mapped_column(
        ForeignKey("master_equipments.id"), default=None, nullable=True
    )
    worksheet_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    certificate_no: Mapped[str | None] = mapped_column(String(50), default=None)
    certificate_file_path: Mapped[str | None] = mapped_column(String(500), default=None)
    release_allowed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="job_items")
    master_equipment: Mapped[MasterEquipment | None] = relationship("MasterEquipment")
    subcontractor: Mapped[Subcontractor | None] = relationship(
        "Subcontractor", back_populates="job_items"
    )
    po_out: Mapped[PurchaseOrderOut | None] = relationship(
        "PurchaseOrderOut", back_populates="job_items"
    )
