from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.order import InvoiceStatus, POStatus, ServiceType


class OrderBase(BaseModel):
    customer_id: int
    quotation_no: str | None = None
    po_no: str | None = None
    po_status: POStatus = POStatus.PENDING
    service_type: ServiceType
    bast_no: str | None = None
    received_date: date | None = None
    target_sla_date: date | None = None
    invoice_status: InvoiceStatus = InvoiceStatus.UNBILLED


class OrderCreate(OrderBase):
    pass


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
