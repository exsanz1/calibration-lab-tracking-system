from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.models.job_item import JobStatus, Scope


class JobItemBase(BaseModel):
    order_id: int
    qr_tag: str
    instrument_name: str
    brand: str | None = None
    model: str | None = None
    serial_number: str
    scope: Scope
    status: JobStatus = JobStatus.RECEIVED
    assigned_tech: str | None = None
    accessories: str | None = "Unit Only"
    intake_condition: str = "GOOD"
    master_equipment_id: int | None = None
    worksheet_file_path: str | None = None
    certificate_no: str | None = None
    certificate_file_path: str | None = None
    release_allowed: bool = False


class JobItemCreate(JobItemBase):
    pass


class JobItemIntake(BaseModel):
    """Schema for adding an instrument during BAST intake (qr_tag is generated automatically)."""

    instrument_name: str
    brand: str | None = None
    model: str | None = None
    serial_number: str
    scope: Scope
    accessories: str | None = "Unit Only"
    intake_condition: str = "GOOD"
    master_equipment_id: int | None = None


class JobItemStatusUpdate(BaseModel):
    """Schema for updating a job item's operational status."""

    status: JobStatus
    assigned_tech: str | None = None
    certificate_no: str | None = None


class JobItemUpdate(BaseModel):
    instrument_name: str | None = None
    brand: str | None = None
    model: str | None = None
    serial_number: str | None = None
    scope: Scope | None = None
    status: JobStatus | None = None
    assigned_tech: str | None = None
    accessories: str | None = None
    intake_condition: str | None = None
    master_equipment_id: int | None = None
    worksheet_file_path: str | None = None
    certificate_no: str | None = None
    certificate_file_path: str | None = None


class JobItemRead(JobItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
