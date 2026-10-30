# ⚙️ CalibTrack - Calibration Laboratory Operational & Tracking System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-Electric_Blue-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Mypy](https://img.shields.io/badge/mypy-checked-green.svg)](http://mypy-lang.org/)
[![Tests](https://img.shields.io/badge/pytest-16%20passed-brightgreen.svg)](https://docs.pytest.org/)

Sistem manajemen operasional dan pelacakan alur kerja laboratorium kalibrasi berbasis web. Dirancang khusus untuk mematuhi tata kelola administrasi **ISO/IEC 17025:2017 / KAN**, ketertelusuran metrologi (*metrological traceability*), dan administrasi *Purchase Order* (PO).

---

## 📌 Batasan Kritis Ruang Lingkup (ISO/IEC 17025 Guardrail)

> [!IMPORTANT]
> **CalibTrack BUKAN mesin kalkulasi ketidakpastian (*uncertainty calculation engine*)**.
> Untuk menghindari kewajiban validasi software rumit di bawah regulasi **ISO/IEC 17025 / KAN**:
> 1. Lembar kerja perhitungan teknis (*worksheet math*) diolah secara eksternal (Excel / CSV) dan disimpan sebagai lampiran berkas.
> 2. Sertifikat resmi bertanda tangan (PDF) diunggah dan dikelola dengan proteksi akses unduh berjenjang.
> 3. Sistem ini murni berfokus pada alur administrasi serah terima (BAST), pelacakan tahapan kalibrasi (Kanban), penegakan PO (*Admin Hold*), ketertelusuran standar master, dan SLA pengerjaan.

---

## 🚀 Fitur Utama

### 1. Pendaftaran Order & BAST Intake Otomatis
* **Dynamic BAST Multi-Item:** Penerimaan banyak instrumen dalam satu dokumen BAST (Berita Acara Serah Terima) lengkap dengan kondisi fisik penerimaan dan kelengkapan aksesoris.
* **Auto QR Tagging:** Pembuatan identifikasi instrumen unik otomatis berformat `QR-{YYYY}-{order_id:04d}-{seq:03d}` (contoh: `QR-2026-0001-001`).
* **Print-Friendly BAST (`GET /orders/{id}/print-bast`):** Tampilan cetak tanda terima siap print (A4) dengan CSS `@media print` untuk kebutuhan fisik laboratorium.

### 2. Papan Kerja Kanban (Workflow Pipeline)
* Pelacakan instrumen visual terbagi dalam 6 tahapan teknis:
  $$\text{RECEIVED} \longrightarrow \text{QUEUED} \longrightarrow \text{CALIBRATING} \longrightarrow \text{REVIEW} \longrightarrow \text{CERT\_READY} \longrightarrow \text{DELIVERED}$$
* **Penyaringan Cepat:** Filter instrumen berdasarkan lingkup kalibrasi (*Scope*), teknisi penanggung jawab, dan tipe layanan (`IN_HOUSE` vs `ON_SITE`).
* **Kinerja Cepat & Arsip Terpisah:** Kolom `DELIVERED` dibatasi pada 30 instrumen terbaru; seluruh riwayat pekerjaan tersimpan permanen di menu **Delivered Archive** (`/kanban/archive`).

### 3. Keamanan Administrasi PO (Admin Hold Guardrail)
* Jika status PO pelanggan masih `PENDING`, sistem otomatis memasang badge **"Hold Admin (PO Pending)"**.
* **Keamanan Dokumen:** Endpoint unduh sertifikat PDF (`GET /job-items/{id}/certificate`) terkunci dengan status **HTTP 403 Forbidden** dan instrumen dilarang berpindah ke status `DELIVERED` sebelum bagian administrasi memvalidasi PO menjadi `RECEIVED`.

### 4. Rantai Ketertelusuran Standar Master (Traceability Guardrail)
* Pada saat penautan master equipment di lembar kerja teknisi:
  * Sistem memvalidasi kesesuaian lingkup kalibrasi (*Scope*: Tekanan, Suhu, Massa, Gaya, Dimensi, dll).
  * Sistem memblokir penautan peralatan master yang berstatus `EXPIRED` atau `IN_CALIBRATION`.
* **Integritas Riwayat:** Standar master yang sudah ditautkan ke job kalibrasi masa lalu dilarang dihapus untuk menjaga keabsahan audit ISO 17025.

### 5. Evaluasi Status Standar Master Otomatis & Peringatan Dini
* Auto-update status master equipment menjadi `EXPIRED` seketika jika `due_date < tanggal hari ini`.
* Badge peringatan visual pada dashboard:
  * 🔴 **EXPIRED:** Jatuh tempo kalibrasi telah lewat.
  * 🔴 **CRITICAL:** Masa berlaku kalibrasi tersisa $\le 30$ hari.
  * 🟡 **WARNING:** Masa berlaku kalibrasi tersisa $\le 60$ hari.
  * 🟢 **ACTIVE:** Masa berlaku kalibrasi aman ($> 60$ hari).

### 6. Quick QR Scan di Lapangan (`/scan`)
* Halaman antarmuka ramah-ponsel (*mobile-friendly*) untuk staf lab dan teknisi.
* Cukup pindai label stiker QR fisik pada instrumen untuk langsung membuka form pembaruan status pengerjaan tanpa perlu mencari manual di Kanban board.

### 7. Ringkasan Peringatan Harian API (`GET /api/alerts/daily`)
* Endpoint JSON terstruktur yang menyediakan:
  1. `sla_alerts`: Instrumen yang mendekati batas waktu pengerjaan ($\le 3$ hari) atau overdue.
  2. `admin_holds`: Sertifikat yang tertahan administrasi PO pelanggan.
  3. `master_alerts`: Standar master yang harus segera dikalibrasi ulang ($\le 60$ hari atau kadaluarsa).
* Siap diintegrasikan dengan cron-job/scheduler untuk bot notifikasi harian **WhatsApp** atau **Telegram**.

---

## 🎨 Identitas Visual (Electric Blue Palette)

CalibTrack dibangun menggunakan Tailwind CSS dengan identitas brand warna *Electric Blue*:
* **Primary Brand:** `#0099FF` (Tombol utama, aksen aktif, border sorotan)
* **Hover Accent:** `#007CE8`
* **Subtle Highlight:** `#F0F8FF` / `#E0F2FE` (Latar badge dan baris terpilih)
* **Canvas Background:** `#F8FAFC`
* **Surface Background:** `#FFFFFF`
* **Typography:** `#0F172A` (Heading/Text) & `#64748B` (Muted/Secondary)

---

## 💻 Panduan Instalasi & Penggunaan

### Cara 1: Menggunakan Script Cepat (Windows `.bat`)
Jika Anda menggunakan Windows, Anda cukup mengklik file batch yang telah disediakan:
* **`run.bat`:** Klik 2x untuk menjalankan server otomatis, menginisialisasi database awal jika belum ada, dan membuka browser ke `http://localhost:8000`.
* **`seed_db.bat`:** Klik 2x untuk mereset dan mengisi ulang database dengan data simulasi laboratorium.
* **`run_tests.bat`:** Klik 2x untuk mengeksekusi 16 unit test (pytest) dan pemeriksaan strict type (mypy).

---

### Cara 2: Menjalankan Secara Manual via Terminal

#### 1. Kloning Repository & Masuk ke Folder Proyek
```bash
git clone https://github.com/exsanz1/calibration-lab-tracking-system.git
cd calibration-lab-tracking-system
```

#### 2. Pasang Dependencies
Pastikan Python 3.11 atau lebih baru telah terpasang:
```bash
pip install -r requirements.txt
```

#### 3. Inisialisasi Database & Data Simulasi
```bash
python seed.py
```
*Perintah ini akan membuat database SQLite `calibration.db` dan mengisi 3 pelanggan industri, 5 standar master acuan, 3 order, dan 6 instrumen kalibrasi contoh.*

#### 4. Jalankan Server Web (Uvicorn)
```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### 5. Buka Aplikasi di Browser
* **Dashboard Operasional:** [http://localhost:8000](http://localhost:8000)
* **Dokumentasi REST API Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Dokumentasi Alternatif ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Pengujian Otomatis & Kualitas Kode

Sistem ini memiliki kepatuhan tipe ketat (**mypy 100%**) dan cakupan pengujian unit otomatis (**pytest**):

```bash
# Menjalankan seluruh pengujian unit
pytest tests/ -v

# Menjalankan type-checker statis
mypy app tests
```

**Hasil Verifikasi:**
* `16 passed in 0.92s` (Cakupan pengujian BAST, Kanban, Guardrail ISO 17025, Admin Hold, File Download Security, Expiration Engine, dan Alert API).
* `Success: no issues found in 36 source files` (Strict typing tanpa error).

---

## 📁 Struktur Direktori Proyek

```text
calibration-lab-tracking-system/
├── app/
│   ├── models/                 # Model database SQLAlchemy 2.0 (Customer, Order, JobItem, MasterEquipment)
│   ├── schemas/                # Skema validasi Pydantic v2 (ORM mode & DTO)
│   ├── routers/                # Endpoint FastAPI (Dashboard, Customers, Orders, BAST, Kanban, JobItems, Equipments, Alerts)
│   ├── services/               # Logika bisnis (Admin Hold, Status Evaluation, Metrological Traceability, Local Storage)
│   ├── templates/              # Antarmuka Jinja2 + Tailwind CSS (BAST, Kanban, Equipments, Dashboard, Scan)
│   ├── database.py             # Konfigurasi engine database SQLite / PostgreSQL
│   ├── templates_config.py     # Konfigurasi rendering template Jinja2
│   └── main.py                 # Titik masuk utama FastAPI app & registrasi router
├── storage/                    # Tempat penyimpanan berkas lokal terisolasi di luar static
│   └── uploads/
│       ├── worksheets/         # Lembar kerja kalkulasi teknis (.xlsx, .xls, .csv)
│       └── certificates/       # Sertifikat resmi (.pdf)
├── tests/                      # Suite pengujian otomatis pytest (Phase 2, Phase 3, Phase 4)
│   ├── conftest.py             # Fixture SQLite in-memory untuk isolasi pengujian
│   ├── test_phase2.py          # Pengujian intake customer, order, dan BAST
│   ├── test_phase3.py          # Pengujian Kanban, protected files, dan traceability
│   └── test_phase4.py          # Pengujian auto-expiration master, guardrail hapus, dan daily alerts
├── plan.md                     # Rencana arsitektur dan spesifikasi teknis
├── requirements.txt            # Daftar pustaka dependency Python
├── seed.py                     # Script seeding data simulasi lab
├── run.bat                     # Script launcher Windows
├── seed_db.bat                 # Script reset database Windows
└── run_tests.bat               # Script pengujian otomatis Windows
```

---

## 📄 Lisensi

Proyek ini dikembangkan untuk kebutuhan operasional laboratorium kalibrasi dan didistribusikan di bawah lisensi internal / open-source sesuai kebijakan organisasi.

