from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.job_item import Scope
from app.models.master_equipment import EquipmentStatus


class MasterEquipmentBase(BaseModel):
    name: str
    serial_number: str
    scope: Scope
    last_cal_date: date | None = None
    due_date: date | None = None
    traceability_body: str | None = None
    status: EquipmentStatus = EquipmentStatus.ACTIVE


class MasterEquipmentCreate(MasterEquipmentBase):
    pass


class MasterEquipmentUpdate(BaseModel):
    name: str | None = None
    serial_number: str | None = None
    scope: Scope | None = None
    last_cal_date: date | None = None
    due_date: date | None = None
    traceability_body: str | None = None
    status: EquipmentStatus | None = None


class MasterEquipmentRead(MasterEquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
