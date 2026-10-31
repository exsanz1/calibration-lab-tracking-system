from __future__ import annotations

from app.services.admin_hold import (
    sync_job_item_release,
    sync_order_job_items_release,
)
from app.services.alerts import generate_daily_alerts
from app.services.doc_generator import (
    generate_ba_docx,
    generate_invoice_docx,
    generate_ordersheet_xlsx,
    generate_penawaran_docx,
    generate_po_keluar_docx,
    generate_tt_docx,
    prepare_docx_template_bytes,
)
from app.services.equipment_status import (
    get_equipment_alert_info,
    sync_and_evaluate_equipment_status,
)
from app.services.number_generator import (
    format_currency_idr,
    format_date_indo,
    format_day_date_indo,
    format_day_indo,
    generate_bast_no,
    generate_certificate_no,
    generate_invoice_no,
    generate_ordersheet_no,
    generate_po_out_no,
    generate_quotation_no,
    generate_tt_no,
)
from app.services.storage import (
    CERTIFICATE_DIR,
    WORKSHEET_DIR,
    init_storage,
    save_certificate,
    save_worksheet,
)
from app.services.traceability import validate_master_equipment

__all__ = [
    "sync_job_item_release",
    "sync_order_job_items_release",
    "init_storage",
    "save_worksheet",
    "save_certificate",
    "WORKSHEET_DIR",
    "CERTIFICATE_DIR",
    "validate_master_equipment",
    "sync_and_evaluate_equipment_status",
    "get_equipment_alert_info",
    "generate_daily_alerts",
    "prepare_docx_template_bytes",
    "generate_penawaran_docx",
    "generate_ordersheet_xlsx",
    "generate_tt_docx",
    "generate_ba_docx",
    "generate_po_keluar_docx",
    "generate_invoice_docx",
    "format_currency_idr",
    "format_date_indo",
    "format_day_indo",
    "format_day_date_indo",
    "generate_quotation_no",
    "generate_ordersheet_no",
    "generate_tt_no",
    "generate_bast_no",
    "generate_invoice_no",
    "generate_po_out_no",
    "generate_certificate_no",
]
