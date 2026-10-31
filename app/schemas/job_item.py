from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.job_item import JobStatus, Scope


class JobItemBase(BaseModel):
    order_id: int
    qr_tag: str
    instrument_name: str
    specification_desc: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str
    scope: Scope
    qty: int = 1
    unit: str = "Unit"
    unit_price: int = 0
    subcontractor_id: int | None = None
    subcon_price: int = 0
    po_out_id: int | None = None
    status: JobStatus = JobStatus.RECEIVED
    assigned_tech: str | None = None
    accessories: str | None = "Unit Only"
    intake_condition: str = "GOOD"
    master_equipment_id: int | None = None
    worksheet_file_path: str | None = None
    certificate_no: str | None = None
    certificate_file_path: str | None = None
    release_allowed: bool = False


class JobItemCreate(BaseModel):
    order_id: int
    qr_tag: str | None = None
    instrument_name: str
    specification_desc: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str
    scope: Scope
    qty: int = 1
    unit: str = "Unit"
    unit_price: int = 0
    subcontractor_id: int | None = None
    subcon_price: int = 0
    po_out_id: int | None = None
    status: JobStatus = JobStatus.RECEIVED
    assigned_tech: str | None = None
    accessories: str | None = "Unit Only"
    intake_condition: str = "GOOD"
    master_equipment_id: int | None = None


class JobItemIntake(BaseModel):
    instrument_name: str
    brand: str | None = None
    model: str | None = None
    serial_number: str
    scope: Scope
    qty: int = 1
    unit: str = "Unit"
    unit_price: int = 0
    specification_desc: str | None = None
    accessories: str | None = "Unit Only"
    intake_condition: str = "GOOD"
    master_equipment_id: int | None = None
    subcontractor_id: int | None = None
    subcon_price: int = 0


class JobItemStatusUpdate(BaseModel):
    status: JobStatus
    assigned_tech: str | None = None
    certificate_no: str | None = None


class JobItemUpdate(BaseModel):
    instrument_name: str | None = None
    specification_desc: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    scope: Scope | None = None
    qty: int | None = None
    unit: str | None = None
    unit_price: int | None = None
    subcontractor_id: int | None = None
    subcon_price: int | None = None
    po_out_id: int | None = None
    status: JobStatus | None = None
    assigned_tech: str | None = None
    accessories: str | None = None
    intake_condition: str | None = None
    master_equipment_id: int | None = None
    certificate_no: str | None = None
    release_allowed: bool | None = None


class JobItemRead(JobItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
