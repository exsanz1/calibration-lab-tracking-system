from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from app.models.job_item import JobItem, JobStatus
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import Order, POStatus
from app.schemas.alert import (
    AdminHoldAlertItem,
    DailyAlertSummary,
    MasterEquipmentAlertItem,
    SLAAlertItem,
)
from app.services.equipment_status import sync_and_evaluate_equipment_status


def generate_daily_alerts(
    db: Session, today: date | None = None
) -> DailyAlertSummary:
    """Generate a comprehensive daily alert summary:

    1. SLA alerts: job_items approaching target_sla_date (<= 3 days) or overdue (excluding DELIVERED).
    2. Admin holds: job_items at CERT_READY blocked by release_allowed == False (po_status == PENDING).
    3. Master alerts: master_equipments expiring within 60 days or already EXPIRED.
    """
    current_today = today or date.today()

    # Step 1: Ensure any overdue master equipment is synchronized to EXPIRED
    sync_and_evaluate_equipment_status(db, current_today)

    # Step 2: SLA Alerts (non-delivered items due in <= 3 days or overdue)
    active_items = (
        db.query(JobItem)
        .join(Order, JobItem.order_id == Order.id)
        .options(joinedload(JobItem.order).joinedload(Order.customer))
        .filter(
            JobItem.status != JobStatus.DELIVERED,
            Order.target_sla_date.isnot(None),
        )
        .all()
    )

    sla_alerts: list[SLAAlertItem] = []
    for item in active_items:
        if item.order.target_sla_date:
            days_diff = (item.order.target_sla_date - current_today).days
            if days_diff <= 3:
                customer_name = (
                    item.order.customer.company_name if item.order.customer else "Unknown Customer"
                )
                sla_alerts.append(
                    SLAAlertItem(
                        item_id=item.id,
                        qr_tag=item.qr_tag,
                        instrument_name=item.instrument_name,
                        serial_number=item.serial_number,
                        customer_name=customer_name,
                        order_id=item.order_id,
                        target_sla_date=item.order.target_sla_date,
                        days_remaining=days_diff,
                        is_overdue=days_diff < 0,
                        status=item.status,
                    )
                )

    sla_alerts.sort(key=lambda x: x.days_remaining)

    # Step 3: Admin Holds (items at CERT_READY blocked by PO Pending / release_allowed == False)
    held_items = (
        db.query(JobItem)
        .join(Order, JobItem.order_id == Order.id)
        .options(joinedload(JobItem.order).joinedload(Order.customer))
        .filter(
            JobItem.status == JobStatus.CERT_READY,
            JobItem.release_allowed.is_(False),
        )
        .all()
    )

    admin_holds: list[AdminHoldAlertItem] = []
    for item in held_items:
        customer_name = (
            item.order.customer.company_name if item.order.customer else "Unknown Customer"
        )
        admin_holds.append(
            AdminHoldAlertItem(
                item_id=item.id,
                qr_tag=item.qr_tag,
                instrument_name=item.instrument_name,
                serial_number=item.serial_number,
                customer_name=customer_name,
                order_id=item.order_id,
                bast_no=item.order.bast_no,
                po_status=item.order.po_status,
                status=item.status,
            )
        )

    # Step 4: Master Equipment Alerts (expiring in <= 60 days or already EXPIRED)
    equipments = db.query(MasterEquipment).all()
    master_alerts: list[MasterEquipmentAlertItem] = []

    for eq in equipments:
        days_until_due: int | None = None
        if eq.due_date:
            days_until_due = (eq.due_date - current_today).days

        if eq.status == EquipmentStatus.EXPIRED or (
            days_until_due is not None and days_until_due < 0
        ):
            alert_level = "EXPIRED"
        elif days_until_due is not None and days_until_due <= 30:
            alert_level = "CRITICAL"
        elif days_until_due is not None and days_until_due <= 60:
            alert_level = "WARNING"
        else:
            continue

        master_alerts.append(
            MasterEquipmentAlertItem(
                equipment_id=eq.id,
                name=eq.name,
                serial_number=eq.serial_number,
                scope=eq.scope,
                status=eq.status,
                due_date=eq.due_date,
                days_until_due=days_until_due,
                alert_level=alert_level,
            )
        )

    # Sort master alerts: EXPIRED first, then by days_until_due ascending
    master_alerts.sort(
        key=lambda x: (
            0 if x.alert_level == "EXPIRED" else (1 if x.alert_level == "CRITICAL" else 2),
            x.days_until_due if x.days_until_due is not None else 9999,
        )
    )

    return DailyAlertSummary(
        generated_at=datetime.now().isoformat(),
        total_sla_alerts=len(sla_alerts),
        total_admin_holds=len(admin_holds),
        total_master_alerts=len(master_alerts),
        sla_alerts=sla_alerts,
        admin_holds=admin_holds,
        master_alerts=master_alerts,
    )
