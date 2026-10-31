from __future__ import annotations

import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.job_item import JobItem
    from app.models.po_out import PurchaseOrderOut


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

    # Stage 1: Penawaran (Quotation)
    job_info: Mapped[str] = mapped_column(String(200), default="Kalibrasi")
    quotation_no: Mapped[str | None] = mapped_column(String(50), default=None)
    quotation_date: Mapped[date | None] = mapped_column(default=None)
    revision_no: Mapped[str] = mapped_column(String(20), default="00")
    notes: Mapped[str | None] = mapped_column(String(500), default="")

    # Stage 2: Purchase Order (PO Masuk Customer)
    po_no: Mapped[str | None] = mapped_column(String(50), default=None)
    po_status: Mapped[POStatus] = mapped_column(default=POStatus.PENDING)
    service_type: Mapped[ServiceType] = mapped_column(default=ServiceType.IN_HOUSE)

    # Stage 3: Ordersheet Internal
    ordersheet_no: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, default=None
    )

    # Stage 4: Penerimaan Alat (Intake BAST)
    received_date: Mapped[date | None] = mapped_column(default=None)
    target_sla_date: Mapped[date | None] = mapped_column(default=None)

    # Stage 6: Pengembalian Alat (Tanda Terima & Berita Acara)
    tt_no: Mapped[str | None] = mapped_column(String(50), default=None)
    returned_date: Mapped[date | None] = mapped_column(default=None)
    bast_no: Mapped[str | None] = mapped_column(String(50), default=None)

    # Stage 7: Penagihan / Invoice
    invoice_no: Mapped[str | None] = mapped_column(String(50), default=None)
    invoice_date: Mapped[date | None] = mapped_column(default=None)
    terms_pembayaran: Mapped[str] = mapped_column(String(50), default="30 Hari")
    invoice_status: Mapped[InvoiceStatus] = mapped_column(default=InvoiceStatus.UNBILLED)

    # Financials (IDR integers)
    subtotal: Mapped[int] = mapped_column(Integer, default=0)
    ppn_percent: Mapped[int] = mapped_column(Integer, default=11)
    ppn_amount: Mapped[int] = mapped_column(Integer, default=0)
    grand_total: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    customer: Mapped[Customer] = relationship("Customer", back_populates="orders")
    job_items: Mapped[list[JobItem]] = relationship(
        "JobItem", back_populates="order", cascade="all, delete-orphan"
    )
    purchase_orders_out: Mapped[list[PurchaseOrderOut]] = relationship(
        "PurchaseOrderOut", back_populates="order"
    )
