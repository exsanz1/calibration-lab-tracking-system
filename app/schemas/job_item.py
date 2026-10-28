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
    worksheet_file_path: str | None = None
    certificate_no: str | None = None
    certificate_file_path: str | None = None
    release_allowed: bool = False


class JobItemCreate(JobItemBase):
    pass


class JobItemRead(JobItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
