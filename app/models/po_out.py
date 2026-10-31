from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.job_item import JobItem
    from app.models.order import Order
    from app.models.subcontractor import Subcontractor


class POOutStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    COMPLETED = "COMPLETED"


class PurchaseOrderOut(Base):
    __tablename__ = "purchase_orders_out"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_out_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    subcontractor_id: Mapped[int] = mapped_column(ForeignKey("subcontractors.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    job_info: Mapped[str] = mapped_column(String(200), default="Kalibrasi")
    po_date: Mapped[date] = mapped_column(default=date.today)
    delivery_date: Mapped[date | None] = mapped_column(default=None)
    vendor_quotation_no: Mapped[str | None] = mapped_column(String(50), default="-")
    notes: Mapped[str | None] = mapped_column(String(500), default="")
    onsite_fee: Mapped[int] = mapped_column(Integer, default=0)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    ppn_amount: Mapped[int] = mapped_column(Integer, default=0)
    grand_total: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[POOutStatus] = mapped_column(default=POOutStatus.DRAFT)

    subcontractor: Mapped[Subcontractor] = relationship(
        "Subcontractor", back_populates="purchase_orders_out"
    )
    order: Mapped[Order] = relationship("Order", back_populates="purchase_orders_out")
    job_items: Mapped[list[JobItem]] = relationship(
        "JobItem", back_populates="po_out"
    )
