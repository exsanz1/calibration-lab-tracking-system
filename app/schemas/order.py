from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.order import InvoiceStatus, POStatus, ServiceType


class OrderBase(BaseModel):
    customer_id: int
    job_info: str = "Kalibrasi"
    quotation_no: str | None = None
    quotation_date: date | None = None
    revision_no: str = "00"
    notes: str | None = ""
    po_no: str | None = None
    po_status: POStatus = POStatus.PENDING
    service_type: ServiceType = ServiceType.IN_HOUSE
    ordersheet_no: str | None = None
    received_date: date | None = None
    target_sla_date: date | None = None
    tt_no: str | None = None
    returned_date: date | None = None
    bast_no: str | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    terms_pembayaran: str = "30 Hari"
    invoice_status: InvoiceStatus = InvoiceStatus.UNBILLED
    subtotal: int = 0
    ppn_percent: int = 11
    ppn_amount: int = 0
    grand_total: int = 0


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_id: int | None = None
    job_info: str | None = None
    quotation_no: str | None = None
    quotation_date: date | None = None
    revision_no: str | None = None
    notes: str | None = None
    po_no: str | None = None
    po_status: POStatus | None = None
    service_type: ServiceType | None = None
    ordersheet_no: str | None = None
    received_date: date | None = None
    target_sla_date: date | None = None
    tt_no: str | None = None
    returned_date: date | None = None
    bast_no: str | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    terms_pembayaran: str | None = None
    invoice_status: InvoiceStatus | None = None
    subtotal: int | None = None
    ppn_percent: int | None = None
    ppn_amount: int | None = None
    grand_total: int | None = None


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
