from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class POStatus(str, enum.Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"


class ServiceType(str, enum.Enum):
    IN_HOUSE = "IN_HOUSE"
    ON_SITE = "ON_SITE"


class InvoiceStatus(str, enum.Enum):
    UNBILLED = "UNBILLED"
    INVOICED = "INVOICED"
    PAID = "PAID"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    quotation_no: Mapped[str | None] = mapped_column(String(50), default=None)
    po_no: Mapped[str | None] = mapped_column(String(50), default=None)
    po_status: Mapped[POStatus] = mapped_column(default=POStatus.PENDING)
    service_type: Mapped[ServiceType] = mapped_column()
    bast_no: Mapped[str | None] = mapped_column(String(50), default=None)
    received_date: Mapped[date | None] = mapped_column(default=None)
    target_sla_date: Mapped[date | None] = mapped_column(default=None)
    invoice_status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.UNBILLED)

    customer: Mapped[Customer] = relationship(back_populates="orders")
    job_items: Mapped[list[JobItem]] = relationship(back_populates="order")
