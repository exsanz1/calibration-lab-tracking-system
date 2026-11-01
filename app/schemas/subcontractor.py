from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SubcontractorBase(BaseModel):
    vendor_name: str
    pic_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class SubcontractorCreate(SubcontractorBase):
    pass


class SubcontractorUpdate(BaseModel):
    vendor_name: str | None = None
    pic_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class SubcontractorRead(SubcontractorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int

