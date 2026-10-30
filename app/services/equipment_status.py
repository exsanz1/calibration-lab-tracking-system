from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.master_equipment import EquipmentStatus, MasterEquipment


def sync_and_evaluate_equipment_status(
    db: Session, today: date | None = None
) -> list[MasterEquipment]:
    """Auto-update master_equipments.status to EXPIRED if due_date < today.

    Commits any updates to the database and returns the list of all master equipments.
    """
    current_today = today or date.today()

    expired_candidates = (
        db.query(MasterEquipment)
        .filter(
            MasterEquipment.due_date.isnot(None),
            MasterEquipment.due_date < current_today,
            MasterEquipment.status != EquipmentStatus.EXPIRED,
        )
        .all()
    )

    if expired_candidates:
        for eq in expired_candidates:
            eq.status = EquipmentStatus.EXPIRED
        db.commit()

    return db.query(MasterEquipment).order_by(MasterEquipment.due_date.asc().nulls_last()).all()


def get_equipment_alert_info(
    eq: MasterEquipment, today: date | None = None
) -> dict[str, Any]:
    """Calculate the real-time alert level, badge label, badge styling classes,

    and days until recalibration due date.
    """
    current_today = today or date.today()

    if eq.due_date is None:
        if eq.status == EquipmentStatus.IN_CALIBRATION:
            return {
                "alert_level": "IN_CALIBRATION",
                "label": "In Calibration",
                "badge_class": "bg-sky-50 text-sky-700 border border-sky-300",
                "days_until_due": None,
            }
        return {
            "alert_level": eq.status.value,
            "label": eq.status.value,
            "badge_class": "bg-slate-100 text-slate-700 border border-slate-300",
            "days_until_due": None,
        }

    days_until_due = (eq.due_date - current_today).days

    if days_until_due < 0 or eq.status == EquipmentStatus.EXPIRED:
        days_ago = abs(days_until_due)
        label = f"Expired ({days_ago}d ago)" if days_until_due < 0 else "Expired"
        return {
            "alert_level": "EXPIRED",
            "label": label,
            "badge_class": "bg-rose-50 text-rose-700 border border-rose-300 font-bold",
            "days_until_due": days_until_due,
        }

    if eq.status == EquipmentStatus.IN_CALIBRATION:
        return {
            "alert_level": "IN_CALIBRATION",
            "label": f"In Calibration ({days_until_due}d due)",
            "badge_class": "bg-sky-50 text-sky-700 border border-sky-300 font-semibold",
            "days_until_due": days_until_due,
        }

    if days_until_due <= 30:
        return {
            "alert_level": "CRITICAL",
            "label": f"Critical ({days_until_due}d left)",
            "badge_class": "bg-rose-50 text-rose-700 border border-rose-300 font-semibold",
            "days_until_due": days_until_due,
        }

    if days_until_due <= 60:
        return {
            "alert_level": "WARNING",
            "label": f"Warning ({days_until_due}d left)",
            "badge_class": "bg-amber-50 text-amber-700 border border-amber-300 font-semibold",
            "days_until_due": days_until_due,
        }

    return {
        "alert_level": "GOOD",
        "label": f"Active ({days_until_due}d left)",
        "badge_class": "bg-emerald-50 text-emerald-700 border border-emerald-300 font-medium",
        "days_until_due": days_until_due,
    }

