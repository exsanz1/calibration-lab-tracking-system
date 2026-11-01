from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.po_out import POOutStatus


class POOutBase(BaseModel):
    po_out_no: str
    subcontractor_id: int
    order_id: int
    job_info: str = "Kalibrasi"
    po_date: date = date.today()
    delivery_date: date | None = None
    vendor_quotation_no: str | None = "-"
    notes: str | None = ""
    onsite_fee: int = 0
    subtotal: int = 0
    ppn_amount: int = 0
    grand_total: int = 0
    status: POOutStatus = POOutStatus.DRAFT


class POOutCreate(BaseModel):
    subcontractor_id: int
    order_id: int
    po_out_no: str | None = None
    job_info: str = "Kalibrasi"
    po_date: date = date.today()
    delivery_date: date | None = None
    vendor_quotation_no: str | None = "-"
    notes: str | None = ""
    onsite_fee: int = 0
    item_ids: list[int] = []


class POOutUpdate(BaseModel):
    po_out_no: str | None = None
    subcontractor_id: int | None = None
    order_id: int | None = None
    job_info: str | None = None
    po_date: date | None = None
    delivery_date: date | None = None
    vendor_quotation_no: str | None = None
    notes: str | None = None
    onsite_fee: int | None = None
    status: POOutStatus | None = None


class POOutRead(POOutBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

