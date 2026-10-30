from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.order import InvoiceStatus, POStatus, ServiceType
from app.schemas.customer import CustomerRead
from app.schemas.job_item import JobItemRead


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


class OrderUpdate(BaseModel):
    customer_id: int | None = None
    quotation_no: str | None = None
    po_no: str | None = None
    po_status: POStatus | None = None
    service_type: ServiceType | None = None
    bast_no: str | None = None
    received_date: date | None = None
    target_sla_date: date | None = None
    invoice_status: InvoiceStatus | None = None


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer: CustomerRead | None = None


class OrderDetailRead(OrderRead):
    job_items: list[JobItemRead] = []
