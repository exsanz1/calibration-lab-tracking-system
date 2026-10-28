# Project Plan: Calibration Lab Operational & Tracking System (Non-Technical Scope)

## 1. Context & Strict Boundaries
Build a web-based operational tracking system for a calibration laboratory. 
**CRITICAL CONSTRAINT:** Do NOT build calculation engines for calibration uncertainty or worksheet math (to avoid ISO/IEC 17025 / KAN software validation issues). Technical worksheets (Excel) and certificates (PDF) are processed externally and only tracked as metadata/file attachments in this system.

## 2. Tech Stack & Standards
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (or SQLModel), Pydantic v2.
- **Database:** SQLite (dev) / PostgreSQL (prod).
- **Frontend:** Jinja2 Templates + Tailwind CSS + HTMX (or Alpine.js) for interactive Kanban without heavy SPA build steps.
- **Code Quality:** Strict type hints (mypy compliant), modular router structure, clean error handling.

## 2.1 Design System & UI Branding
The UI must strictly align with the laboratory's electric blue brand identity:
- **Color Palette (Tailwind Configuration):**
  - `brand-primary`: `#0099FF` (Buttons, active navigation items, QR code highlights, primary borders)
  - `brand-hover`: `#007CE8`
  - `brand-subtle`: `#F0F8FF` / `#E0F2FE` (Badge backgrounds, selected row highlights)
  - `canvas`: `#F8FAFC` (Dashboard body background)
  - `surface`: `#FFFFFF` (Card panels, Kanban columns, tables)
  - `text-main`: `#0F172A` (Headings, primary data labels)
  - `text-muted`: `#64748B` (Secondary text, metadata, serial numbers)
- **Status Indicators (High Contrast Badges):**
  - `In-Progress / Calibrating`: `brand-primary` / `brand-subtle`
  - `Cert Ready / Approved`: `emerald-600` / `emerald-50`
  - `Hold Admin (PO Pending)`: `amber-600` / `amber-50`
  - `Overdue / Master Expired`: `rose-600` / `rose-50`
- **Component Styling:**
  - Sidebar/Navbar: Clean white with `#0099FF` logo accent and left-border indicators on active menus.
  - Kanban Columns: Minimalist gray cards (`#FFFFFF`) over subtle slate canvas (`#F8FAFC`) with colored top border status lines.
  - Form & Inputs: Crisp borders (`border-slate-300`) with `focus:ring-2 focus:ring-[#0099FF]` and `focus:border-[#0099FF]`.

## 3. Core Database Schema
1. **`customers`**: `id`, `company_name`, `pic_name`, `phone`, `email`, `address`.
2. **`orders` (Quotation & PO)**: 
   - `id`, `customer_id`, `quotation_no`, `po_no`, `po_status` (`PENDING`, `RECEIVED`), `service_type` (`IN_HOUSE`, `ON_SITE`), `bast_no`, `received_date`, `target_sla_date`, `invoice_status` (`UNBILLED`, `INVOICED`, `PAID`).
3. **`job_items` (Alat Customer)**:
   - `id`, `order_id`, `qr_tag`, `instrument_name`, `brand`, `model`, `serial_number`, `scope` (`PRESSURE`, `FORCE`, `TEMP`, `MASS`, `DIMENSION`, `OTHER`).
   - `status` (`RECEIVED`, `QUEUED`, `CALIBRATING`, `REVIEW`, `CERT_READY`, `HOLD_ADMIN`, `DELIVERED`).
   - `assigned_tech`, `worksheet_file_path`, `certificate_no`, `certificate_file_path`, `release_allowed` (Boolean - true only if PO/Payment criteria met).
4. **`master_equipments` (Alat Standar Lab)**:
   - `id`, `name`, `serial_number`, `scope`, `last_cal_date`, `due_date`, `traceability_body` (e.g., SNSU-BSN / LK), `status` (`ACTIVE`, `EXPIRED`, `IN_CALIBRATION`).

---

## 4. Implementation Phases

### Phase 1: Project Scaffolding & Database Models
- Setup directory structure (`app/`, `app/models/`, `app/schemas/`, `app/routers/`, `app/templates/`, `tests/`).
- Implement database connection, SQLAlchemy models, and Pydantic v2 schemas for the 4 core tables.
- Create seed script (`seed.py`) with dummy calibration data (sample customers, pressure/force gauges, and master equipments).
- Ensure zero type errors.

### Phase 2: Order Intake, BAST & PO Administration
- Create CRUD endpoints and UI for `customers` and `orders`.
- Implement BAST (Berita Acara Serah Terima) intake form: input multiple `job_items` under one `order` and auto-generate unique `qr_tag` IDs.
- Implement Admin Hold Logic: if `po_status == PENDING`, flag `release_allowed = False` on certificates even if technical status reaches `CERT_READY`.

### Phase 3: Kanban Job Tracking & File Archiving
- Build Kanban Board UI grouped by `job_items.status` (`RECEIVED` -> `QUEUED` -> `CALIBRATING` -> `REVIEW` -> `CERT_READY` -> `DELIVERED`).
- Add filter by `scope`, `assigned_tech`, and `service_type` (`IN_HOUSE` vs `ON_SITE`).
- Add local file upload endpoint per `job_item` to attach the completed Excel Worksheet and signed PDF Certificate.

### Phase 4: Master Equipment Guardrail & SLA Alerts
- Create CRUD and dashboard for `master_equipments`.
- Implement automated check: highlight master equipments expiring in <= 60 days (`WARNING`) and <= 30 days (`CRITICAL`), and auto-mark as `EXPIRED` if past `due_date`.
- Create a summary endpoint (`/api/alerts/daily`) returning JSON of:
  1. `job_items` approaching `target_sla_date` (<= 3 days) or overdue.
  2. `job_items` stuck in `CERT_READY` but blocked by `po_status == PENDING`.
  3. `master_equipments` needing recalibration.
  *(To be consumed by WhatsApp/Telegram webhook scheduler).*