from __future__ import annotations

from datetime import date

ROMAN_MONTHS = [
    "",
    "I",
    "II",
    "III",
    "IV",
    "V",
    "VI",
    "VII",
    "VIII",
    "IX",
    "X",
    "XI",
    "XII",
]

INDONESIAN_DAYS = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu",
}

INDONESIAN_MONTHS = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


def get_roman_month(m: int) -> str:
    if 1 <= m <= 12:
        return ROMAN_MONTHS[m]
    return "I"


def format_date_indo(dt: date | None) -> str:
    if not dt:
        return "-"
    return f"{dt.day} {INDONESIAN_MONTHS.get(dt.month, '')} {dt.year}"


def format_day_indo(dt: date | None) -> str:
    if not dt:
        return "-"
    return INDONESIAN_DAYS.get(dt.weekday(), "")


def format_day_date_indo(dt: date | None) -> str:
    if not dt:
        return "-"
    day_name = INDONESIAN_DAYS.get(dt.weekday(), "")
    return f"{day_name}, {dt.day} {INDONESIAN_MONTHS.get(dt.month, '')} {dt.year}"


def format_currency_idr(amount: int) -> str:
    return f"{amount:,.0f}".replace(",", ".")


def generate_quotation_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    roman = get_roman_month(target_dt.month)
    return f"{seq:04d}/PNW-NSI/{roman}/{target_dt.year}"


def generate_ordersheet_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    mmyy = target_dt.strftime("%m%y")
    return f"K.{seq:04d}.{mmyy}"


def generate_tt_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    roman = get_roman_month(target_dt.month)
    yy = target_dt.strftime("%y")
    return f"{seq:04d}/TT-NSI/{roman}/{yy}"


def generate_bast_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    roman = get_roman_month(target_dt.month)
    return f"{seq:04d}/BAP-NSI/{roman}/{target_dt.year}"


def generate_invoice_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    roman = get_roman_month(target_dt.month)
    return f"{seq:04d}/INV-NSI/{roman}/{target_dt.year}"


def generate_po_out_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    roman = get_roman_month(target_dt.month)
    return f"{seq:03d}/PO-NSI/{roman}/{target_dt.year}"


def generate_certificate_no(seq: int, dt: date | None = None) -> str:
    target_dt = dt or date.today()
    mmyy = target_dt.strftime("%m%y")
    return f"NSI.{seq:04d}.{mmyy}"
