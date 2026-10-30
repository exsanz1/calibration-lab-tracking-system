from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import Order, POStatus, ServiceType
from app.services.equipment_status import (
    get_equipment_alert_info,
    sync_and_evaluate_equipment_status,
)


def _seed_phase4_data(db: Session) -> dict[str, int]:
    """Helper to seed test data for Phase 4 scenarios."""
    today = date.today()

    # 1. Customer
    cust = Customer(
        company_name="PT Petro Energy",
        pic_name="Bambang",
        phone="0811223344",
        email="bambang@petro.com",
    )
    db.add(cust)
    db.flush()

    # 2. Master Equipments in different status and due dates
    # Due in 15 days (<= 30d -> CRITICAL)
    eq_crit = MasterEquipment(
        name="Critical Fluke Calibrator",
        serial_number="ME-P4-CRIT",
        scope=Scope.PRESSURE,
        last_cal_date=today - timedelta(days=350),
        due_date=today + timedelta(days=15),
        status=EquipmentStatus.ACTIVE,
    )
    # Due in 45 days (<= 60d -> WARNING)
    eq_warn = MasterEquipment(
        name="Warning Torque Standard",
        serial_number="ME-P4-WARN",
        scope=Scope.FORCE,
        last_cal_date=today - timedelta(days=320),
        due_date=today + timedelta(days=45),
        status=EquipmentStatus.ACTIVE,
    )
    # Due in 120 days (> 60d -> GOOD / ACTIVE)
    eq_good = MasterEquipment(
        name="Healthy Weight Standard",
        serial_number="ME-P4-GOOD",
        scope=Scope.MASS,
        last_cal_date=today - timedelta(days=50),
        due_date=today + timedelta(days=120),
        status=EquipmentStatus.ACTIVE,
    )
    # Due yesterday with ACTIVE status (should auto-expire)
    eq_expired_active = MasterEquipment(
        name="Overdue Pyrometer",
        serial_number="ME-P4-EXPACT",
        scope=Scope.TEMP,
        last_cal_date=today - timedelta(days=370),
        due_date=today - timedelta(days=5),
        status=EquipmentStatus.ACTIVE,
    )
    # Marked In Calibration
    eq_in_cal = MasterEquipment(
        name="Gauge In Calibration",
        serial_number="ME-P4-INCAL",
        scope=Scope.DIMENSION,
        last_cal_date=today - timedelta(days=360),
        due_date=today + timedelta(days=20),
        status=EquipmentStatus.IN_CALIBRATION,
    )

    db.add_all([eq_crit, eq_warn, eq_good, eq_expired_active, eq_in_cal])
    db.flush()

    # 3. Orders:
    # Order 1: PO Pending, target SLA due in 2 days (<= 3d -> SLA Alert)
    o_urgent = Order(
        customer_id=cust.id,
        quotation_no="Q-P4-001",
        po_status=POStatus.PENDING,
        service_type=ServiceType.IN_HOUSE,
        target_sla_date=today + timedelta(days=2),
    )
    # Order 2: PO Pending, target SLA overdue by 3 days (Overdue SLA Alert)
    o_overdue = Order(
        customer_id=cust.id,
        quotation_no="Q-P4-002",
        po_status=POStatus.PENDING,
        service_type=ServiceType.IN_HOUSE,
        target_sla_date=today - timedelta(days=3),
    )
    # Order 3: PO Received, target SLA far away (15 days)
    o_safe = Order(
        customer_id=cust.id,
        quotation_no="Q-P4-003",
        po_status=POStatus.RECEIVED,
        service_type=ServiceType.IN_HOUSE,
        target_sla_date=today + timedelta(days=15),
    )
    db.add_all([o_urgent, o_overdue, o_safe])
    db.flush()

    # 4. Job Items:
    # Item 1: In CALIBRATING under urgent order (triggers SLA alert)
    item_urgent = JobItem(
        order_id=o_urgent.id,
        qr_tag="QR-P4-0001-001",
        instrument_name="Digital Manometer",
        serial_number="SN-DM-01",
        scope=Scope.PRESSURE,
        status=JobStatus.CALIBRATING,
        master_equipment_id=eq_crit.id,
    )
    # Item 2: At CERT_READY but release_allowed is False (triggers Admin Hold alert)
    item_held = JobItem(
        order_id=o_urgent.id,
        qr_tag="QR-P4-0001-002",
        instrument_name="Pressure Transmitter",
        serial_number="SN-PT-02",
        scope=Scope.PRESSURE,
        status=JobStatus.CERT_READY,
        release_allowed=False,
    )
    # Item 3: Under overdue order in QUEUED (triggers Overdue SLA alert)
    item_overdue = JobItem(
        order_id=o_overdue.id,
        qr_tag="QR-P4-0002-001",
        instrument_name="Force Cell",
        serial_number="SN-FC-03",
        scope=Scope.FORCE,
        status=JobStatus.QUEUED,
    )
    # Item 4: DELIVERED item under overdue order (MUST be excluded from SLA alerts)
    item_delivered = JobItem(
        order_id=o_overdue.id,
        qr_tag="QR-P4-0002-002",
        instrument_name="Torque Wrench",
        serial_number="SN-TW-04",
        scope=Scope.FORCE,
        status=JobStatus.DELIVERED,
        release_allowed=True,
    )
    # Item 5: Safe item
    item_safe = JobItem(
        order_id=o_safe.id,
        qr_tag="QR-P4-0003-001",
        instrument_name="Precision Balance",
        serial_number="SN-PB-05",
        scope=Scope.MASS,
        status=JobStatus.CALIBRATING,
        release_allowed=True,
    )

    db.add_all([item_urgent, item_held, item_overdue, item_delivered, item_safe])
    db.commit()

    return {
        "cust_id": cust.id,
        "eq_crit_id": eq_crit.id,
        "eq_warn_id": eq_warn.id,
        "eq_good_id": eq_good.id,
        "eq_expired_id": eq_expired_active.id,
        "eq_in_cal_id": eq_in_cal.id,
        "item_urgent_id": item_urgent.id,
        "item_held_id": item_held.id,
        "item_overdue_id": item_overdue.id,
        "item_delivered_id": item_delivered.id,
    }


# ==========================================
# 1. TEST EQUIPMENT STATUS HELPER & AUTO-EXPIRATION
# ==========================================


def test_equipment_status_auto_expiration_and_badges(db_session: Session) -> None:
    today = date.today()

    # Active equipment with due_date in the past
    overdue_eq = MasterEquipment(
        name="Auto-Expire Test Standard",
        serial_number="SN-TEST-EXP-01",
        scope=Scope.PRESSURE,
        due_date=today - timedelta(days=2),
        status=EquipmentStatus.ACTIVE,
    )
    db_session.add(overdue_eq)
    db_session.commit()

    assert overdue_eq.status == EquipmentStatus.ACTIVE

    # Execute sync helper
    sync_and_evaluate_equipment_status(db_session)
    db_session.expire_all()

    refreshed = db_session.get(MasterEquipment, overdue_eq.id)
    assert refreshed is not None
    assert refreshed.status == EquipmentStatus.EXPIRED

    # Check alert info badges
    badge_expired = get_equipment_alert_info(refreshed, today)
    assert badge_expired["alert_level"] == "EXPIRED"
    assert "Expired" in badge_expired["label"]

    # Critical <= 30 days
    crit_eq = MasterEquipment(
        name="Critical Test",
        serial_number="SN-CRIT-TEST",
        scope=Scope.TEMP,
        due_date=today + timedelta(days=10),
        status=EquipmentStatus.ACTIVE,
    )
    badge_crit = get_equipment_alert_info(crit_eq, today)
    assert badge_crit["alert_level"] == "CRITICAL"
    assert badge_crit["days_until_due"] == 10

    # Warning <= 60 days
    warn_eq = MasterEquipment(
        name="Warning Test",
        serial_number="SN-WARN-TEST",
        scope=Scope.MASS,
        due_date=today + timedelta(days=45),
        status=EquipmentStatus.ACTIVE,
    )
    badge_warn = get_equipment_alert_info(warn_eq, today)
    assert badge_warn["alert_level"] == "WARNING"
    assert badge_warn["days_until_due"] == 45

    # Good > 60 days
    good_eq = MasterEquipment(
        name="Good Test",
        serial_number="SN-GOOD-TEST",
        scope=Scope.FORCE,
        due_date=today + timedelta(days=90),
        status=EquipmentStatus.ACTIVE,
    )
    badge_good = get_equipment_alert_info(good_eq, today)
    assert badge_good["alert_level"] == "GOOD"
    assert badge_good["days_until_due"] == 90


# ==========================================
# 2. TEST MASTER EQUIPMENT WEB CRUD & ISO GUARDRAILS
# ==========================================


def test_master_equipment_web_crud_and_delete_guardrail(
    client: TestClient, db_session: Session
) -> None:
    ids = _seed_phase4_data(db_session)

    # 1. GET /equipments
    res = client.get("/equipments")
    assert res.status_code == 200
    assert "Master Equipment Standards" in res.text
    assert "ME-P4-CRIT" in res.text
    assert "ME-P4-WARN" in res.text

    # 2. GET /equipments/create
    res = client.get("/equipments/create")
    assert res.status_code == 200
    assert "Register Master Equipment Standard" in res.text

    # 3. POST /equipments (Create new)
    create_payload = {
        "name": "New Web Created Standard",
        "serial_number": "SN-NEW-WEB-01",
        "scope": "PRESSURE",
        "last_cal_date": date.today().isoformat(),
        "due_date": (date.today() + timedelta(days=365)).isoformat(),
        "traceability_body": "KAN LK-999-IDN",
        "status": "ACTIVE",
    }
    res_post = client.post("/equipments", data=create_payload, follow_redirects=True)
    assert res_post.status_code == 200
    assert "New Web Created Standard" in res_post.text

    # Verify duplicate serial number rejected
    res_dup = client.post("/equipments", data=create_payload)
    assert res_dup.status_code == 200
    assert "already registered" in res_dup.text

    # 4. GET /equipments/{id}/edit
    eq_id = ids["eq_good_id"]
    res_edit = client.get(f"/equipments/{eq_id}/edit")
    assert res_edit.status_code == 200
    assert "Healthy Weight Standard" in res_edit.text

    # 5. POST /equipments/{id}/edit (Update)
    update_payload = {
        "name": "Healthy Weight Standard Renamed",
        "serial_number": "ME-P4-GOOD",
        "scope": "MASS",
        "last_cal_date": (date.today() - timedelta(days=60)).isoformat(),
        "due_date": (date.today() + timedelta(days=300)).isoformat(),
        "traceability_body": "Updated Traceability Body",
        "status": "ACTIVE",
    }
    res_update = client.post(
        f"/equipments/{eq_id}/edit", data=update_payload, follow_redirects=True
    )
    assert res_update.status_code == 200
    assert "Healthy Weight Standard Renamed" in res_update.text

    # 6. POST /equipments/{id}/delete Guardrail:
    # Attempting to delete eq_crit which is linked to item_urgent -> blocked!
    crit_id = ids["eq_crit_id"]
    res_del_blocked = client.post(f"/equipments/{crit_id}/delete", follow_redirects=True)
    assert res_del_blocked.status_code == 200
    assert "Cannot+delete" in res_del_blocked.text or "Cannot delete" in res_del_blocked.text
    # Still exists in DB
    assert db_session.get(MasterEquipment, crit_id) is not None

    # Deleting unlinked equipment succeeds
    unlinked_eq = MasterEquipment(
        name="Unlinked Standalone",
        serial_number="ME-UNLINKED-01",
        scope=Scope.OTHER,
        status=EquipmentStatus.ACTIVE,
    )
    db_session.add(unlinked_eq)
    db_session.commit()
    unlinked_id = unlinked_eq.id

    res_del_ok = client.post(f"/equipments/{unlinked_id}/delete", follow_redirects=True)
    assert res_del_ok.status_code == 200
    db_session.expire_all()
    assert db_session.get(MasterEquipment, unlinked_id) is None


# ==========================================
# 3. TEST MASTER EQUIPMENT REST API CRUD
# ==========================================


def test_master_equipment_rest_api_crud(client: TestClient, db_session: Session) -> None:
    ids = _seed_phase4_data(db_session)

    # 1. List
    res = client.get("/api/master-equipments")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 5

    # Filter by scope
    res_filt = client.get("/api/master-equipments?scope=PRESSURE")
    assert res_filt.status_code == 200
    for it in res_filt.json():
        assert it["scope"] == "PRESSURE"

    # 2. Create API
    payload = {
        "name": "API Precision Calibrator",
        "serial_number": "SN-API-TEST-99",
        "scope": "DIMENSION",
        "due_date": (date.today() + timedelta(days=200)).isoformat(),
        "status": "ACTIVE",
    }
    res_create = client.post("/api/master-equipments", json=payload)
    assert res_create.status_code == 201
    created_id = res_create.json()["id"]
    assert res_create.json()["name"] == "API Precision Calibrator"

    # 3. Read Single
    res_get = client.get(f"/api/master-equipments/{created_id}")
    assert res_get.status_code == 200
    assert res_get.json()["serial_number"] == "SN-API-TEST-99"

    # 4. Update API
    res_put = client.put(
        f"/api/master-equipments/{created_id}",
        json={"name": "API Precision Calibrator Renamed"},
    )
    assert res_put.status_code == 200
    assert res_put.json()["name"] == "API Precision Calibrator Renamed"

    # 5. Delete API guardrail: fail if linked
    crit_id = ids["eq_crit_id"]
    res_del_fail = client.delete(f"/api/master-equipments/{crit_id}")
    assert res_del_fail.status_code == 400
    assert "Cannot delete master equipment" in res_del_fail.json()["detail"]

    # Delete API succeed if unlinked
    res_del_ok = client.delete(f"/api/master-equipments/{created_id}")
    assert res_del_ok.status_code == 204


# ==========================================
# 4. TEST DAILY SUMMARY ALERTS API (/api/alerts/daily)
# ==========================================


def test_daily_summary_alerts_endpoint(client: TestClient, db_session: Session) -> None:
    ids = _seed_phase4_data(db_session)

    res = client.get("/api/alerts/daily")
    assert res.status_code == 200
    data = res.json()

    # Structure checks
    assert "generated_at" in data
    assert "total_sla_alerts" in data
    assert "total_admin_holds" in data
    assert "total_master_alerts" in data
    assert "sla_alerts" in data
    assert "admin_holds" in data
    assert "master_alerts" in data

    # 1. Check SLA Alerts:
    # item_urgent (due in 2d) and item_overdue (overdue 3d) should be present.
    # item_delivered (DELIVERED) MUST NOT be present.
    # item_safe (due in 15d) MUST NOT be present.
    sla_item_ids = [a["item_id"] for a in data["sla_alerts"]]
    assert ids["item_urgent_id"] in sla_item_ids
    assert ids["item_overdue_id"] in sla_item_ids
    assert ids["item_delivered_id"] not in sla_item_ids

    # Verify is_overdue flag
    overdue_alert = next(a for a in data["sla_alerts"] if a["item_id"] == ids["item_overdue_id"])
    assert overdue_alert["is_overdue"] is True
    assert overdue_alert["days_remaining"] < 0

    urgent_alert = next(a for a in data["sla_alerts"] if a["item_id"] == ids["item_urgent_id"])
    assert urgent_alert["is_overdue"] is False
    assert urgent_alert["days_remaining"] == 2

    # 2. Check Admin Holds:
    # item_held (CERT_READY and release_allowed=False) should be present.
    admin_hold_ids = [h["item_id"] for h in data["admin_holds"]]
    assert ids["item_held_id"] in admin_hold_ids

    # 3. Check Master Equipment Alerts:
    # eq_crit (15d -> CRITICAL), eq_warn (45d -> WARNING), eq_expired (EXPIRED) must be in master_alerts.
    # eq_good (120d -> GOOD) must NOT be in master_alerts.
    master_alert_eq_ids = [m["equipment_id"] for m in data["master_alerts"]]
    assert ids["eq_crit_id"] in master_alert_eq_ids
    assert ids["eq_warn_id"] in master_alert_eq_ids
    assert ids["eq_expired_id"] in master_alert_eq_ids
    assert ids["eq_good_id"] not in master_alert_eq_ids

    # Check alert levels
    crit_alert = next(m for m in data["master_alerts"] if m["equipment_id"] == ids["eq_crit_id"])
    assert crit_alert["alert_level"] == "CRITICAL"

    warn_alert = next(m for m in data["master_alerts"] if m["equipment_id"] == ids["eq_warn_id"])
    assert warn_alert["alert_level"] == "WARNING"

    exp_alert = next(m for m in data["master_alerts"] if m["equipment_id"] == ids["eq_expired_id"])
    assert exp_alert["alert_level"] == "EXPIRED"


# ==========================================
# 5. TEST DASHBOARD INTEGRATION
# ==========================================


def test_dashboard_alerts_display(client: TestClient, db_session: Session) -> None:
    _seed_phase4_data(db_session)

    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Operational Dashboard header
    assert "Operational Dashboard" in html
    # SLA alert banner
    assert "SLA Deadline Alert" in html
    # Master standard alert banner
    assert "Master Standards Recalibration Alert" in html
    # Admin Hold alert banner
    assert "Admin Hold In Effect" in html
    # Master standard navigation item
    assert "Master Standards" in html
