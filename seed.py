"""Seed the database with sample calibration lab data."""

from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import InvoiceStatus, Order, POStatus, ServiceType


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # --- Customers ---
        c1 = Customer(
            company_name="PT Pertamina Hulu Energi",
            pic_name="Budi Santoso",
            phone="021-5551234",
            email="budi.santoso@pertamina.com",
            address="Jl. Medan Merdeka Timur No.1A, Jakarta",
        )
        c2 = Customer(
            company_name="PT Krakatau Steel",
            pic_name="Rina Wijaya",
            phone="0254-396888",
            email="rina.wijaya@krakatau.co.id",
            address="Jl. Industri No.5, Cilegon, Banten",
        )
        c3 = Customer(
            company_name="PT Pupuk Kaltim",
            pic_name="Hadi Purnomo",
            phone="0548-41200",
            email="hadi.purnomo@pupukkaltim.com",
            address="Jl. James Simandjuntak No.1, Bontang",
        )
        db.add_all([c1, c2, c3])
        db.flush()

        today = date.today()

        # --- Orders ---
        o1 = Order(
            customer_id=c1.id,
            quotation_no="Q-2026-0045",
            po_no="PO/PHE/2026/0312",
            po_status=POStatus.RECEIVED,
            service_type=ServiceType.IN_HOUSE,
            bast_no="BAST-2026-0045",
            received_date=today - timedelta(days=5),
            target_sla_date=today + timedelta(days=9),
            invoice_status=InvoiceStatus.UNBILLED,
        )
        o2 = Order(
            customer_id=c2.id,
            quotation_no="Q-2026-0046",
            po_status=POStatus.PENDING,
            service_type=ServiceType.ON_SITE,
            received_date=today - timedelta(days=2),
            target_sla_date=today + timedelta(days=12),
        )
        o3 = Order(
            customer_id=c3.id,
            quotation_no="Q-2026-0047",
            po_no="PO/PKT/2026/0088",
            po_status=POStatus.RECEIVED,
            service_type=ServiceType.IN_HOUSE,
            bast_no="BAST-2026-0047",
            received_date=today - timedelta(days=10),
            target_sla_date=today + timedelta(days=4),
            invoice_status=InvoiceStatus.INVOICED,
        )
        db.add_all([o1, o2, o3])
        db.flush()

        # --- Job Items ---
        job_items = [
            JobItem(
                order_id=o1.id,
                qr_tag="QR-2026-0045-001",
                instrument_name="Pressure Gauge",
                brand="WIKA",
                model="232.50",
                serial_number="PG-W-20240115",
                scope=Scope.PRESSURE,
                status=JobStatus.CALIBRATING,
                assigned_tech="Andi Pratama",
            ),
            JobItem(
                order_id=o1.id,
                qr_tag="QR-2026-0045-002",
                instrument_name="Pressure Transmitter",
                brand="Emerson",
                model="3051T",
                serial_number="PT-E-20230987",
                scope=Scope.PRESSURE,
                status=JobStatus.QUEUED,
            ),
            JobItem(
                order_id=o2.id,
                qr_tag="QR-2026-0046-001",
                instrument_name="Force Gauge",
                brand="Shimpo",
                model="FGV-50XY",
                serial_number="FG-S-20241122",
                scope=Scope.FORCE,
                status=JobStatus.RECEIVED,
            ),
            JobItem(
                order_id=o2.id,
                qr_tag="QR-2026-0046-002",
                instrument_name="Torque Wrench",
                brand="Tohnichi",
                model="QL50N-MH",
                serial_number="TW-T-20240508",
                scope=Scope.FORCE,
                status=JobStatus.RECEIVED,
            ),
            JobItem(
                order_id=o3.id,
                qr_tag="QR-2026-0047-001",
                instrument_name="Thermocouple",
                brand="Fluke",
                model="1523",
                serial_number="TC-F-20240301",
                scope=Scope.TEMP,
                status=JobStatus.CERT_READY,
                assigned_tech="Dewi Lestari",
                certificate_no="CERT-2026-0098",
                release_allowed=True,
            ),
            JobItem(
                order_id=o3.id,
                qr_tag="QR-2026-0047-002",
                instrument_name="Analytical Balance",
                brand="Mettler Toledo",
                model="ME204",
                serial_number="AB-MT-20240712",
                scope=Scope.MASS,
                status=JobStatus.REVIEW,
                assigned_tech="Dewi Lestari",
            ),
        ]
        db.add_all(job_items)

        # --- Master Equipments ---
        master_equipments = [
            MasterEquipment(
                name="Dead Weight Tester",
                serial_number="ME-DWT-001",
                scope=Scope.PRESSURE,
                last_cal_date=today - timedelta(days=200),
                due_date=today + timedelta(days=165),
                traceability_body="SNSU-BSN",
                status=EquipmentStatus.ACTIVE,
            ),
            MasterEquipment(
                name="Universal Testing Machine 100kN",
                serial_number="ME-UTM-001",
                scope=Scope.FORCE,
                last_cal_date=today - timedelta(days=330),
                due_date=today + timedelta(days=35),
                traceability_body="SNSU-BSN",
                status=EquipmentStatus.ACTIVE,
            ),
            MasterEquipment(
                name="SPRT Reference Thermometer",
                serial_number="ME-SPRT-001",
                scope=Scope.TEMP,
                last_cal_date=today - timedelta(days=350),
                due_date=today + timedelta(days=15),
                traceability_body="SNSU-BSN",
                status=EquipmentStatus.ACTIVE,
            ),
            MasterEquipment(
                name="Standard Weight Set F1",
                serial_number="ME-SWS-001",
                scope=Scope.MASS,
                last_cal_date=today - timedelta(days=400),
                due_date=today - timedelta(days=35),
                traceability_body="LK-BI",
                status=EquipmentStatus.EXPIRED,
            ),
            MasterEquipment(
                name="Gauge Block Set Grade K",
                serial_number="ME-GBS-001",
                scope=Scope.DIMENSION,
                last_cal_date=today - timedelta(days=100),
                due_date=today + timedelta(days=265),
                traceability_body="SNSU-BSN",
                status=EquipmentStatus.ACTIVE,
            ),
        ]
        db.add_all(master_equipments)

        db.commit()
        print(f"Seeded {len([c1, c2, c3])} customers")
        print(f"Seeded {len([o1, o2, o3])} orders")
        print(f"Seeded {len(job_items)} job items")
        print(f"Seeded {len(master_equipments)} master equipments")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
