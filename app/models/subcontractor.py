from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.job_item import JobItem
    from app.models.po_out import PurchaseOrderOut


class Subcontractor(Base):
    __tablename__ = "subcontractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String(200), index=True)
    pic_name: Mapped[str | None] = mapped_column(String(100), default=None)  # Attn
    phone: Mapped[str | None] = mapped_column(String(50), default=None)
    email: Mapped[str | None] = mapped_column(String(100), default=None)
    address: Mapped[str | None] = mapped_column(String(500), default=None)

    job_items: Mapped[list[JobItem]] = relationship(
        "JobItem", back_populates="subcontractor"
    )
    purchase_orders_out: Mapped[list[PurchaseOrderOut]] = relationship(
        "PurchaseOrderOut", back_populates="subcontractor"
    )

