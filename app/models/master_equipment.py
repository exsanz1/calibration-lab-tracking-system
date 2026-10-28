from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.job_item import Scope


class EquipmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    IN_CALIBRATION = "IN_CALIBRATION"


class MasterEquipment(Base):
    __tablename__ = "master_equipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    scope: Mapped[Scope] = mapped_column()
    last_cal_date: Mapped[date | None] = mapped_column(default=None)
    due_date: Mapped[date | None] = mapped_column(default=None)
    traceability_body: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[EquipmentStatus] = mapped_column(default=EquipmentStatus.ACTIVE)
