from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.order import InvoiceStatus, Order, POStatus, ServiceType

# Isolated test database in memory
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_dashboard_page():
    res = client.get("/")
    assert res.status_code == 200
    assert "Operational Dashboard" in res.text
    assert "CalibTrack" in res.text


# ==========================================
# CUSTOMER CRUD TESTS
# ==========================================

def test_customer_api_crud():
    # 1. Create
    payload = {
        "company_name": "PT Test Lab",
        "pic_name": "Ahmad",
        "phone": "08123456789",
        "email": "ahmad@testlab.com",
        "address": "Jakarta",
    }
    res = client.post("/api/customers", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["id"] > 0
    assert created["company_name"] == "PT Test Lab"
    cust_id = created["id"]

    # 2. Read list
    res = client.get("/api/customers")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 3. Read single
    res = client.get(f"/api/customers/{cust_id}")
    assert res.status_code == 200
    assert res.json()["company_name"] == "PT Test Lab"

    # 4. Update
    update_payload = {
        "company_name": "PT Test Lab Updated",
        "pic_name": "Ahmad",
        "phone": "08123456789",
        "email": "ahmad@testlab.com",
        "address": "Bandung",
    }
    res = client.put(f"/api/customers/{cust_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json()["company_name"] == "PT Test Lab Updated"

    # 5. Delete
    res = client.delete(f"/api/customers/{cust_id}")
    assert res.status_code == 204
    assert client.get(f"/api/customers/{cust_id}").status_code == 404


def test_customer_html_views():
    # Create via form POST
    res = client.post(
        "/customers/save",
        data={
            "customer_id": 0,
            "company_name": "PT HTML Customer",
            "pic_name": "Siti",
            "phone": "0899999",
            "email": "siti@html.com",
            "address": "Surabaya",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert "PT HTML Customer" in res.text

    # List page
    res = client.get("/customers")
    assert res.status_code == 200
    assert "PT HTML Customer" in res.text

    # Create page
    res = client.get("/customers/create")
    assert res.status_code == 200
    assert "Add New Customer" in res.text


# ==========================================
# ORDER CRUD & ADMIN HOLD TESTS
# ==========================================

def test_order_crud_and_admin_hold_logic():
    # Setup Customer
    cust_res = client.post(
        "/api/customers",
        json={
            "company_name": "PT Industri Nusantara",
            "pic_name": "Dewi",
            "phone": "021-998877",
        },
    )
    cust_id = cust_res.json()["id"]

    # 1. Create Order with POStatus == PENDING (Admin Hold Active)
    order_payload = {
        "customer_id": cust_id,
        "quotation_no": "Q-2026-9001",
        "po_no": None,
        "po_status": "PENDING",
        "service_type": "IN_HOUSE",
        "bast_no": "BAST-2026-9001",
        "received_date": str(date.today()),
        "target_sla_date": str(date.today()),
        "invoice_status": "UNBILLED",
    }
    res = client.post("/api/orders", json=order_payload)
    assert res.status_code == 201
    order_id = res.json()["id"]
    assert res.json()["po_status"] == "PENDING"

    # 2. Add multiple instruments via BAST API
    intake_items = [
        {
            "instrument_name": "Digital Pressure Gauge",
            "brand": "Fluke",
            "model": "700G",
            "serial_number": "SN-DPG-01",
            "scope": "PRESSURE",
        },
        {
            "instrument_name": "Load Cell 50kN",
            "brand": "HBM",
            "model": "C2",
            "serial_number": "SN-LC-02",
            "scope": "FORCE",
        },
    ]
    res = client.post(f"/api/orders/{order_id}/items", json=intake_items)
    assert res.status_code == 201
    items = res.json()
    assert len(items) == 2
    item1_id = items[0]["id"]
    item2_id = items[1]["id"]

    # Verify auto-generated QR tag format: QR-{YYYY}-{order_id:04d}-{seq:03d}
    year = date.today().year
    assert items[0]["qr_tag"] == f"QR-{year}-{order_id:04d}-001"
    assert items[1]["qr_tag"] == f"QR-{year}-{order_id:04d}-002"

    # Both items must have release_allowed = False because PO is PENDING
    assert items[0]["release_allowed"] is False
    assert items[1]["release_allowed"] is False

    # 3. Technician marks Item 1 as CERT_READY, but PO is still PENDING
    status_res = client.patch(
        f"/api/job-items/{item1_id}/status",
        json={"status": "CERT_READY", "certificate_no": "CERT-2026-TEST01"},
    )
    assert status_res.status_code == 200
    updated_item = status_res.json()
    assert updated_item["status"] == "CERT_READY"
    # CRITICAL: Admin Hold must BLOCK release!
    assert updated_item["release_allowed"] is False

    # 4. Now Customer PO is RECEIVED -> Admin updates Order
    order_update_res = client.patch(
        f"/api/orders/{order_id}",
        json={"po_status": "RECEIVED", "po_no": "PO/CUST/2026/001"},
    )
    assert order_update_res.status_code == 200
    assert order_update_res.json()["po_status"] == "RECEIVED"

    # Verify Item 1 (CERT_READY) is now automatically allowed for release!
    item1_check = client.get(f"/api/job-items/{item1_id}").json()
    assert item1_check["release_allowed"] is True

    # Item 2 is still RECEIVED (not CERT_READY), so its release_allowed remains False
    item2_check = client.get(f"/api/job-items/{item2_id}").json()
    assert item2_check["release_allowed"] is False

    # 5. If Order PO is reverted to PENDING -> all items must revert to release_allowed = False
    client.patch(f"/api/orders/{order_id}", json={"po_status": "PENDING"})
    item1_reverted = client.get(f"/api/job-items/{item1_id}").json()
    assert item1_reverted["release_allowed"] is False


def test_bast_html_form_intake():
    # Setup Customer & Order
    cust = client.post(
        "/api/customers",
        json={
            "company_name": "PT BAST Form Test",
            "pic_name": "Joko",
            "phone": "08123456",
        },
    ).json()

    order = client.post(
        "/api/orders",
        json={
            "customer_id": cust["id"],
            "quotation_no": "Q-2026-BAST-FORM",
            "po_status": "RECEIVED",
            "service_type": "ON_SITE",
            "bast_no": "BAST-2026-0099",
        },
    ).json()
    order_id = order["id"]

    # View BAST page
    page_res = client.get(f"/orders/{order_id}/bast")
    assert page_res.status_code == 200
    assert "Berita Acara Serah Terima" in page_res.text
    assert "PT BAST Form Test" in page_res.text

    # Post multiple items via BAST HTML form
    form_items = [
        {
            "instrument_name": "Temperature Calibrator",
            "brand": "Ametek",
            "model": "RTC-159",
            "serial_number": "SN-TC-8899",
            "scope": "TEMP",
        },
        {
            "instrument_name": "Standard Weight 1kg",
            "brand": "Troemner",
            "model": "F1",
            "serial_number": "SN-SW-1000",
            "scope": "MASS",
        },
    ]

    save_res = client.post(
        f"/orders/{order_id}/bast/save",
        data={"items_json": json.dumps(form_items)},
        follow_redirects=True,
    )
    assert save_res.status_code == 200
    assert "Temperature Calibrator" in save_res.text
    assert "Standard Weight 1kg" in save_res.text
    year = date.today().year
    assert f"QR-{year}-{order_id:04d}-001" in save_res.text
    assert f"QR-{year}-{order_id:04d}-002" in save_res.text
