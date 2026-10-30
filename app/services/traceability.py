from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.job_item import Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment


def validate_master_equipment(
    db: Session, master_equipment_id: int, item_scope: Scope
) -> MasterEquipment:
    """Validate that master equipment exists, is ACTIVE, and matches instrument scope."""
    equipment = db.get(MasterEquipment, master_equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=404,
            detail=f"Master equipment with id {master_equipment_id} not found",
        )

    if equipment.status != EquipmentStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Master equipment '{equipment.name}' cannot be used because its status is "
                f"{equipment.status.value}. Only ACTIVE master standards are permitted under ISO/IEC 17025."
            ),
        )

    if equipment.scope != item_scope:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Scope mismatch: Instrument is in scope {item_scope.value}, but master equipment "
                f"'{equipment.name}' is in scope {equipment.scope.value}."
            ),
        )

    return equipment
