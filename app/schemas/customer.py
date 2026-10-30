from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CustomerBase(BaseModel):
    company_name: str
    pic_name: str
    phone: str
    email: str | None = None
    address: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    company_name: str | None = None
    pic_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
