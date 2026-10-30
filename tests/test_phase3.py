from __future__ import annotations

import io
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import Order, POStatus, ServiceType


def _seed_base_data(db: Session) -> tuple[Customer, Order, MasterEquipment, MasterEquipment, MasterEquipment]:
    """Helper to seed base customer, order and master equipments for tests."""
    c = Customer(
        company_name="PT Petrokimia Test",
        pic_name="Iwan",
        phone="031-778899",
        address="Gresik",
    )
    db.add(c)
    db.flush()

    # Active Master Standard (Pressure)
    m_active = MasterEquipment(
        name="Active Deadweight Tester",
        serial_number="ME-ACT-01",
        scope=Scope.PRESSURE,
        last_cal_date=date.today() - timedelta(days=100),
        due_date=date.today() + timedelta(days=265),
        status=EquipmentStatus.ACTIVE,
    )
    # Expired Master Standard (Pressure)
    m_expired = MasterEquipment(
        name="Expired Pressure Calibrator",
        serial_number="ME-EXP-01",
        scope=Scope.PRESSURE,
        last_cal_date=date.today() - timedelta(days=400),
        due_date=date.today() - timedelta(days=35),
        status=EquipmentStatus.EXPIRED,
    )
    # Active Master Standard (Temp)
    m_temp = MasterEquipment(
        name="Active Dry Block Temp Calibrator",
        serial_number="ME-TEMP-01",
        scope=Scope.TEMP,
        last_cal_date=date.today() - timedelta(days=50),
        due_date=date.today() + timedelta(days=315),
        status=EquipmentStatus.ACTIVE,
    )
    db.add_all([m_active, m_expired, m_temp])
    db.flush()

    # Order with POStatus PENDING (Admin Hold Active)
    o = Order(
        customer_id=c.id,
        quotation_no="Q-2026-PH3-01",
        po_status=POStatus.PENDING,
        service_type=ServiceType.IN_HOUSE,
        bast_no="BAST-2026-PH3-01",
        received_date=date.today(),
    )
    db.add(o)
    db.commit()
    return c, o, m_active, m_expired, m_temp


def test_kanban_board_rendering_and_columns(client: TestClient, db_session: Session) -> None:
    c, o, m_active, _, _ = _seed_base_data(db_session)

    # Create job items in different stages
    item1 = JobItem(
        order_id=o.id,
        qr_tag="QR-2026-0001-001",
        instrument_name="Digital Manometer",
        serial_number="SN-DM-01",
        scope=Scope.PRESSURE,
        status=JobStatus.RECEIVED,
        assigned_tech="Andi",
        release_allowed=False,
    )
    item2 = JobItem(
        order_id=o.id,
        qr_tag="QR-2026-0001-002",
        instrument_name="Pressure Gauge",
        serial_number="SN-PG-02",
        scope=Scope.PRESSURE,
        status=JobStatus.HOLD_ADMIN,
        assigned_tech="Andi",
        release_allowed=False,
    )
    db_session.add_all([item1, item2])
    db_session.commit()

    res = client.get("/kanban")
    assert res.status_code == 200
    # Must render the 6 standard technical columns
    assert "RECEIVED" in res.text
    assert "QUEUED" in res.text
    assert "CALIBRATING" in res.text
    assert "REVIEW" in res.text
    assert "CERT READY" in res.text
    assert "DELIVERED" in res.text
    # HOLD_ADMIN must NOT be a column header
    assert "HOLD ADMIN</h3>" not in res.text
    # But the amber Hold Admin badge must be rendered for release_allowed == False
    assert "Hold Admin (PO Pending)" in res.text

    # Test filtering by scope
    res_filtered = client.get("/kanban?scope=TEMP")
    assert res_filtered.status_code == 200
    assert "Digital Manometer" not in res_filtered.text

    res_matching = client.get("/kanban?scope=PRESSURE")
    assert res_matching.status_code == 200
    assert "Digital Manometer" in res_matching.text


def test_master_equipment_traceability_guardrail(client: TestClient, db_session: Session) -> None:
    _, o, m_active, m_expired, m_temp = _seed_base_data(db_session)

    item = JobItem(
        order_id=o.id,
        qr_tag="QR-2026-0001-010",
        instrument_name="Pressure Transmitter",
        serial_number="SN-PT-10",
        scope=Scope.PRESSURE,
        status=JobStatus.CALIBRATING,
    )
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    # 1. Linking matching ACTIVE master equipment succeeds
    res_ok = client.post(
        f"/job-items/{item_id}/link-master",
        data={"master_equipment_id": m_active.id},
        follow_redirects=True,
    )
    assert res_ok.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(JobItem, item_id)
    assert refreshed is not None
    assert refreshed.master_equipment_id == m_active.id

    # 2. Linking EXPIRED master equipment fails with 400 Bad Request
    res_expired = client.post(
        f"/job-items/{item_id}/link-master",
        data={"master_equipment_id": m_expired.id},
    )
    assert res_expired.status_code == 400
    assert "EXPIRED" in res_expired.json()["detail"]

    # 3. Linking master equipment with mismatched scope fails with 400 Bad Request
    res_scope_mismatch = client.post(
        f"/job-items/{item_id}/link-master",
        data={"master_equipment_id": m_temp.id},
    )
    assert res_scope_mismatch.status_code == 400
    assert "Scope mismatch" in res_scope_mismatch.json()["detail"]


def test_protected_file_storage_and_download_guardrail(client: TestClient, db_session: Session) -> None:
    _, o, _, _, _ = _seed_base_data(db_session)

    # Item under PO PENDING order -> release_allowed is False
    item = JobItem(
        order_id=o.id,
        qr_tag="QR-2026-0001-020",
        instrument_name="Hydraulic Gauge",
        serial_number="SN-HG-20",
        scope=Scope.PRESSURE,
        status=JobStatus.CERT_READY,
        release_allowed=False,
    )
    db_session.add(item)
    db_session.commit()
    item_id = item.id

    # 1. Upload technical worksheet (Excel/CSV)
    fake_csv = io.BytesIO(b"Calibration Point,Standard,Unit\n0,0,0\n50,50.1,50\n")
    ws_res = client.post(
        f"/job-items/{item_id}/upload-worksheet",
        files={"file": ("worksheet.csv", fake_csv, "text/csv")},
        follow_redirects=True,
    )
    assert ws_res.status_code == 200

    # Technician can download worksheet
    ws_dl = client.get(f"/job-items/{item_id}/worksheet")
    assert ws_dl.status_code == 200
    assert b"Calibration Point" in ws_dl.content

    # 2. Upload signed PDF Certificate
    fake_pdf = io.BytesIO(b"%PDF-1.4 Fake PDF Certificate Content for Testing")
    cert_res = client.post(
        f"/job-items/{item_id}/upload-certificate",
        data={"certificate_no": "CERT-2026-9999"},
        files={"file": ("cert.pdf", fake_pdf, "application/pdf")},
        follow_redirects=True,
    )
    assert cert_res.status_code == 200

    # 3. CRITICAL GUARDRAIL: Certificate download MUST return 403 Forbidden when release_allowed == False!
    cert_dl_blocked = client.get(f"/job-items/{item_id}/certificate")
    assert cert_dl_blocked.status_code == 403
    assert "Admin Hold" in cert_dl_blocked.json()["detail"]

    # 4. CRITICAL GUARDRAIL: Cannot transition to DELIVERED when release_allowed == False!
    deliver_blocked = client.post(
        f"/job-items/{item_id}/status",
        data={"status": "DELIVERED"},
    )
    assert deliver_blocked.status_code == 403
    assert "restricted by Admin Hold" in deliver_blocked.json()["detail"]

    # 5. Admin marks Customer PO as RECEIVED -> release_allowed becomes True
    client.patch(f"/api/orders/{o.id}", json={"po_status": "RECEIVED"})

    # Now Certificate download MUST succeed (200 OK)!
    cert_dl_ok = client.get(f"/job-items/{item_id}/certificate")
    assert cert_dl_ok.status_code == 200
    assert cert_dl_ok.content.startswith(b"%PDF-1.4")

    # Now transition to DELIVERED succeeds!
    deliver_ok = client.post(
        f"/job-items/{item_id}/status",
        data={"status": "DELIVERED"},
        follow_redirects=True,
    )
    assert deliver_ok.status_code == 200
    db_session.expire_all()
    refreshed_item = db_session.get(JobItem, item_id)
    assert refreshed_item is not None
    assert refreshed_item.status == JobStatus.DELIVERED


def test_qr_scan_page_flow(client: TestClient, db_session: Session) -> None:
    _, o, _, _, _ = _seed_base_data(db_session)

    item = JobItem(
        order_id=o.id,
        qr_tag="QR-2026-SCAN-001",
        instrument_name="Precision Barometer",
        serial_number="SN-PB-909",
        scope=Scope.PRESSURE,
        status=JobStatus.QUEUED,
        release_allowed=False,
    )
    db_session.add(item)
    db_session.commit()

    # 1. Access QR scanner main page
    scan_index = client.get("/scan")
    assert scan_index.status_code == 200
    assert "Quick QR Scanner" in scan_index.text

    # 2. Access valid QR code scan page
    scan_detail = client.get("/scan/QR-2026-SCAN-001")
    assert scan_detail.status_code == 200
    assert "Precision Barometer" in scan_detail.text
    assert "SN-PB-909" in scan_detail.text
    assert "Mobile Scanner" in scan_detail.text

    # 3. Access non-existent QR tag returns 404
    scan_404 = client.get("/scan/NON-EXISTENT-TAG")
    assert scan_404.status_code == 404
