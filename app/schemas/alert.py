from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.job_item import JobStatus, Scope
from app.models.master_equipment import EquipmentStatus
from app.models.order import POStatus


class SLAAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    qr_tag: str
    instrument_name: str
    serial_number: str
    customer_name: str
    order_id: int
    target_sla_date: date | None
    days_remaining: int
    is_overdue: bool
    status: JobStatus


class AdminHoldAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: int
    qr_tag: str
    instrument_name: str
    serial_number: str
    customer_name: str
    order_id: int
    bast_no: str | None
    po_status: POStatus
    status: JobStatus


class MasterEquipmentAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int
    name: str
    serial_number: str
    scope: Scope
    status: EquipmentStatus
    due_date: date | None
    days_until_due: int | None
    alert_level: str


class DailyAlertSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: str
    total_sla_alerts: int
    total_admin_holds: int
    total_master_alerts: int
    sla_alerts: list[SLAAlertItem]
    admin_holds: list[AdminHoldAlertItem]
    master_alerts: list[MasterEquipmentAlertItem]
