"""Seed the database with sample calibration lab data, subcontractors, and 7-stage orders."""

from datetime import date, timedelta

from app.database import Base, SessionLocal, engine
from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import InvoiceStatus, Order, POStatus, ServiceType
from app.models.po_out import POOutStatus, PurchaseOrderOut
from app.models.subcontractor import Subcontractor


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        today = date.today()

        # --- 1. Customers ---
        c1 = Customer(
            company_name="PT Pertamina Hulu Energi",
            pic_name="Budi Santoso",
            phone="021-5551234",
            email="budi.santoso@pertamina.com",
            address="Jl. Medan Merdeka Timur No.1A, Jakarta Pusat 10110",
        )
        c2 = Customer(
            company_name="PT Krakatau Steel (Persero) Tbk",
            pic_name="Rina Wijaya",
            phone="0254-396888",
            email="rina.wijaya@krakatau.co.id",
            address="Kawasan Industri Krakatau Steel, Jl. Industri No.5, Cilegon, Banten",
        )
        c3 = Customer(
            company_name="PT Pupuk Kalimantan Timur",
            pic_name="Hadi Purnomo",
            phone="0548-41200",
            email="hadi.purnomo@pupukkaltim.com",
            address="Jl. James Simandjuntak No.1, Bontang, Kalimantan Timur",
        )
        customers = [c1, c2, c3]
        db.add_all(customers)
        db.flush()

        # --- 2. Subcontractors (Subcount Partners) ---
        sub1 = Subcontractor(
            vendor_name="PT. Metrologi Akurasi Presisi",
            pic_name="Ir. Hendra Gunawan",
            phone="021-89831234",
            email="hendra@map-kalibrasi.com",
            address="Kawasan Industri Jababeka II, Blok C-15, Cikarang, Bekasi",
        )
        sub2 = Subcontractor(
            vendor_name="PT. Standar Kalibrasi Mandiri",
            pic_name="Siti Rahmawati, S.T.",
            phone="021-75908877",
            email="marketing@skm-lab.co.id",
            address="Jl. RS. Fatmawati No. 45, Cilandak, Jakarta Selatan 12430",
        )
        subcontractors = [sub1, sub2]
        db.add_all(subcontractors)
        db.flush()

        # --- 3. Master Equipments (Standards) ---
        m1 = MasterEquipment(
            name="Dead Weight Tester",
            serial_number="ME-DWT-001",
            scope=Scope.PRESSURE,
            last_cal_date=today - timedelta(days=200),
            due_date=today + timedelta(days=165),
            traceability_body="SNSU-BSN",
            status=EquipmentStatus.ACTIVE,
        )
        m2 = MasterEquipment(
            name="Universal Testing Machine 100kN",
            serial_number="ME-UTM-001",
            scope=Scope.FORCE,
            last_cal_date=today - timedelta(days=330),
            due_date=today + timedelta(days=35),
            traceability_body="SNSU-BSN",
            status=EquipmentStatus.ACTIVE,
        )
        m3 = MasterEquipment(
            name="SPRT Reference Thermometer",
            serial_number="ME-SPRT-001",
            scope=Scope.TEMP,
            last_cal_date=today - timedelta(days=350),
            due_date=today + timedelta(days=15),
            traceability_body="SNSU-BSN",
            status=EquipmentStatus.ACTIVE,
        )
        m4 = MasterEquipment(
            name="Standard Weight Set F1",
            serial_number="ME-SWS-001",
            scope=Scope.MASS,
            last_cal_date=today - timedelta(days=400),
            due_date=today - timedelta(days=35),
            traceability_body="LK-BI",
            status=EquipmentStatus.EXPIRED,
        )
        m5 = MasterEquipment(
            name="Gauge Block Set Grade K",
            serial_number="ME-GBS-001",
            scope=Scope.DIMENSION,
            last_cal_date=today - timedelta(days=100),
            due_date=today + timedelta(days=265),
            traceability_body="SNSU-BSN",
            status=EquipmentStatus.ACTIVE,
        )
        master_equipments = [m1, m2, m3, m4, m5]
        db.add_all(master_equipments)
        db.flush()

        # --- 4. Orders (Representing 7-Stage Pipeline) ---
        # Order 1: Completed through Stage 7 (Invoiced)
        o1 = Order(
            customer_id=c1.id,
            job_info="Kalibrasi",
            quotation_no="0211/PNW-NSI/X/2026",
            quotation_date=today - timedelta(days=25),
            revision_no="00",
            notes="Sertifikat hardcopy 1 rangkap dan softcopy PDF",
            po_no="PO/PHE/2026/0312",
            po_status=POStatus.RECEIVED,
            service_type=ServiceType.IN_HOUSE,
            ordersheet_no="K.0156.1026",
            received_date=today - timedelta(days=20),
            target_sla_date=today - timedelta(days=5),
            tt_no="0285/TT-NSI/IX/26",
            returned_date=today - timedelta(days=3),
            bast_no="0189/BAP-NSI/IX/2026",
            invoice_no="0182/INV-NSI/IX/2026",
            invoice_date=today - timedelta(days=2),
            terms_pembayaran="30 Hari",
            invoice_status=InvoiceStatus.INVOICED,
            subtotal=0,
            ppn_percent=11,
            ppn_amount=0,
            grand_total=0,
        )

        # Order 2: At Stage 2 (PO Pending / Hold Admin)
        o2 = Order(
            customer_id=c2.id,
            job_info="Kalibrasi On-Site",
            quotation_no="0212/PNW-NSI/X/2026",
            quotation_date=today - timedelta(days=7),
            revision_no="00",
            notes="Jadwal kalibrasi on-site menunggu konfirmasi PO",
            po_status=POStatus.PENDING,
            service_type=ServiceType.ON_SITE,
            ordersheet_no="K.0157.1026",
            received_date=today - timedelta(days=2),
            target_sla_date=today + timedelta(days=12),
            invoice_status=InvoiceStatus.UNBILLED,
            subtotal=0,
            ppn_percent=11,
            ppn_amount=0,
            grand_total=0,
        )

        # Order 3: At Stage 5 (Calibration In Progress & Outsourced items)
        o3 = Order(
            customer_id=c3.id,
            job_info="Kalibrasi & Subcontractor",
            quotation_no="0213/PNW-NSI/X/2026",
            quotation_date=today - timedelta(days=15),
            revision_no="00",
            notes="Item analytical balance disubkonkan ke lab rekanan terakreditasi KAN",
            po_no="PO/PKT/2026/0088",
            po_status=POStatus.RECEIVED,
            service_type=ServiceType.IN_HOUSE,
            ordersheet_no="K.0158.1026",
            received_date=today - timedelta(days=10),
            target_sla_date=today + timedelta(days=4),
            invoice_status=InvoiceStatus.UNBILLED,
            subtotal=0,
            ppn_percent=11,
            ppn_amount=0,
            grand_total=0,
        )
        orders = [o1, o2, o3]
        db.add_all(orders)
        db.flush()

        # --- 5. Job Items ---
        # Items for Order 1 (All ready, BAST generated)
        item1_1 = JobItem(
            order_id=o1.id,
            qr_tag="QR-2026-0045-001",
            instrument_name="Pressure Gauge",
            specification_desc="Pressure Gauge Dial 4 inch Range 0 - 100 bar, Conn 1/2 NPT",
            brand="WIKA",
            model="232.50",
            serial_number="PG-W-20240115",
            scope=Scope.PRESSURE,
            status=JobStatus.CERT_READY,
            assigned_tech="Andi Pratama",
            accessories="Fitting Adapter 1/2 to 1/4",
            intake_condition="GOOD",
            master_equipment_id=m1.id,
            certificate_no="NSI.0478.1026",
            qty=2,
            unit="Unit",
            unit_price=450000,
            subcon_price=0,
            release_allowed=True,
        )
        item1_2 = JobItem(
            order_id=o1.id,
            qr_tag="QR-2026-0045-002",
            instrument_name="Pressure Transmitter",
            specification_desc="Smart Pressure Transmitter Range 0 - 250 bar Out 4-20mA HART",
            brand="Emerson Rosemount",
            model="3051T",
            serial_number="PT-E-20230987",
            scope=Scope.PRESSURE,
            status=JobStatus.CERT_READY,
            assigned_tech="Andi Pratama",
            accessories="Bracket & Cable Gland",
            intake_condition="GOOD",
            master_equipment_id=m1.id,
            certificate_no="NSI.0479.1026",
            qty=1,
            unit="Unit",
            unit_price=1250000,
            subcon_price=0,
            release_allowed=True,
        )

        # Items for Order 2 (PO Pending -> Admin Hold)
        item2_1 = JobItem(
            order_id=o2.id,
            qr_tag="QR-2026-0046-001",
            instrument_name="Digital Force Gauge",
            specification_desc="Digital Force Gauge Kapasitas 500 N Akurasi 0.2% F.S",
            brand="Shimpo",
            model="FGV-50XY",
            serial_number="FG-S-20241122",
            scope=Scope.FORCE,
            status=JobStatus.HOLD_ADMIN,
            accessories="Standard Hook & Extension Rod",
            intake_condition="SCRATCHED_CASING",
            master_equipment_id=m2.id,
            qty=1,
            unit="Unit",
            unit_price=850000,
            subcon_price=0,
            release_allowed=False,
        )
        item2_2 = JobItem(
            order_id=o2.id,
            qr_tag="QR-2026-0046-002",
            instrument_name="Torque Wrench",
            specification_desc="Adjustable Click Torque Wrench Range 10 - 50 Nm",
            brand="Tohnichi",
            model="QL50N-MH",
            serial_number="TW-T-20240508",
            scope=Scope.FORCE,
            status=JobStatus.HOLD_ADMIN,
            accessories="Plastic Carrying Case",
            intake_condition="GOOD",
            master_equipment_id=m2.id,
            qty=1,
            unit="Unit",
            unit_price=700000,
            subcon_price=0,
            release_allowed=False,
        )

        # Items for Order 3 (In-house & Subcontracted)
        item3_1 = JobItem(
            order_id=o3.id,
            qr_tag="QR-2026-0047-001",
            instrument_name="Precision Thermocouple",
            specification_desc="Reference Thermocouple Type K Range -50 to 600 deg C",
            brand="Fluke",
            model="1523",
            serial_number="TC-F-20240301",
            scope=Scope.TEMP,
            status=JobStatus.CALIBRATING,
            assigned_tech="Dewi Lestari",
            accessories="Mini TC Connector Cable",
            intake_condition="GOOD",
            master_equipment_id=m3.id,
            qty=1,
            unit="Unit",
            unit_price=950000,
            subcon_price=0,
            release_allowed=True,
        )
        item3_2 = JobItem(
            order_id=o3.id,
            qr_tag="QR-2026-0047-002",
            instrument_name="Electronic Analytical Balance",
            specification_desc="Electronic Analytical Balance Kapasitas 220g Ketelitian 0.1mg",
            brand="Mettler Toledo",
            model="ME204",
            serial_number="AB-MT-20240712",
            scope=Scope.MASS,
            status=JobStatus.QUEUED,
            assigned_tech="Dewi Lestari",
            accessories="Power Adapter & Draft Shield",
            intake_condition="GOOD",
            master_equipment_id=m4.id,
            qty=1,
            unit="Unit",
            unit_price=1750000,
            subcontractor_id=sub1.id,
            subcon_price=1200000,
            release_allowed=True,
        )

        job_items = [item1_1, item1_2, item2_1, item2_2, item3_1, item3_2]
        db.add_all(job_items)
        db.flush()

        # --- 6. Recalculate Order Financials ---
        for o in orders:
            subtot = sum(it.unit_price * it.qty for it in o.job_items)
            ppn = int(subtot * (o.ppn_percent / 100.0))
            o.subtotal = subtot
            o.ppn_amount = ppn
            o.grand_total = subtot + ppn

        # --- 7. Purchase Order Out (Subcount PO to Vendor) ---
        po_out1 = PurchaseOrderOut(
            po_out_no="070/PO-NSI/IX/2026",
            subcontractor_id=sub1.id,
            order_id=o3.id,
            job_info="Kalibrasi",
            po_date=today - timedelta(days=6),
            delivery_date=today + timedelta(days=2),
            vendor_quotation_no="QUO-MAP-2026-098",
            notes="Mohon sertifikat dikirim softcopy terlebih dahulu ke lab@namsae.co.id",
            onsite_fee=0,
            subtotal=1200000,
            ppn_amount=132000,
            grand_total=1332000,
            status=POOutStatus.ISSUED,
        )
        db.add(po_out1)
        db.flush()

        # Link item3_2 to po_out1
        item3_2.po_out_id = po_out1.id

        db.commit()
        print(f"[OK] Seeded {len(customers)} customers")
        print(f"[OK] Seeded {len(subcontractors)} subcontractors")
        print(f"[OK] Seeded {len(master_equipments)} master equipments")
        print(f"[OK] Seeded {len(orders)} orders (7-stage pipeline)")
        print(f"[OK] Seeded {len(job_items)} job items")
        print(f"[OK] Seeded 1 PO Keluar ({po_out1.po_out_no})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
