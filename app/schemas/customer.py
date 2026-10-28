from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerBase(BaseModel):
    company_name: str
    pic_name: str
    phone: str
    email: str | None = None
    address: str | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
