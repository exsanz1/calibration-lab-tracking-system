from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.order import Order
from app.models.subcontractor import Subcontractor
from app.schemas.job_item import (
    JobItemIntake,
    JobItemRead,
    JobItemStatusUpdate,
)
from app.services.admin_hold import sync_job_item_release
from app.services.number_generator import generate_certificate_no
from app.templates_config import templates

router = APIRouter()


def _recalc_order_financials(order: Order) -> None:
    subtot = sum(it.unit_price * it.qty for it in order.job_items)
    ppn = int(subtot * (order.ppn_percent / 100.0))
    order.subtotal = subtot
    order.ppn_amount = ppn
    order.grand_total = subtot + ppn


def _get_next_sequence(db: Session, order_id: int) -> int:
    """Find the next available sequence number for this order to prevent QR collisions."""
    existing_items = (
        db.query(JobItem.qr_tag).filter(JobItem.order_id == order_id).all()
    )
    max_seq = 0
    for (qr,) in existing_items:
        match = re.search(r"-(\d+)$", qr)
        if match:
            seq_val = int(match.group(1))
            if seq_val > max_seq:
                max_seq = seq_val
    return max(max_seq, len(existing_items)) + 1


def _generate_qr_tag(order_id: int, sequence: int) -> str:
    year = date.today().year
    return f"QR-{year}-{order_id:04d}-{sequence:03d}"


# --- HTML Page Endpoints ---


@router.get("/orders/{order_id}/bast", response_class=HTMLResponse)
def page_bast_form(
    order_id: int, request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    existing_items = (
        db.query(JobItem)
        .options(joinedload(JobItem.subcontractor))
        .filter(JobItem.order_id == order_id)
        .order_by(JobItem.id.asc())
        .all()
    )
    subcontractors = (
        db.query(Subcontractor).order_by(Subcontractor.vendor_name).all()
    )
    return templates.TemplateResponse(
        request=request,
        name="bast/form.html",
        context={
            "order": order,
            "existing_items": existing_items,
            "subcontractors": subcontractors,
            "scopes": list(Scope),
        },
    )


@router.post("/orders/{order_id}/items/{item_id}/edit")
def action_edit_order_item(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    instrument_name: str = Form(...),
    specification_desc: str = Form(""),
    brand: str = Form(""),
    model: str = Form(""),
    serial_number: str = Form(...),
    scope: str = Form(...),
    qty: int = Form(1),
    unit: str = Form("Unit"),
    unit_price: int = Form(0),
    subcontractor_id: str = Form(""),
    subcon_price: int = Form(0),
    accessories: str = Form("Unit Only"),
    intake_condition: str = Form("GOOD"),
    certificate_no: str = Form(""),
    redirect_to: str = Form(""),
) -> RedirectResponse:
    item = db.get(JobItem, item_id)
    if not item or item.order_id != order_id:
        raise HTTPException(status_code=404, detail="Item not found")

    order = (
        db.query(Order)
        .options(joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    item.instrument_name = instrument_name.strip()
    item.specification_desc = specification_desc.strip() or None
    item.brand = brand.strip() or None
    item.model = model.strip() or None
    item.serial_number = serial_number.strip()
    item.scope = Scope(scope)
    item.qty = max(1, qty)
    item.unit = unit.strip() or "Unit"
    item.unit_price = max(0, unit_price)

    parsed_sub_id = (
        int(subcontractor_id.strip())
        if subcontractor_id and subcontractor_id.strip().isdigit()
        else None
    )
    item.subcontractor_id = parsed_sub_id
    item.subcon_price = max(0, subcon_price)
    item.accessories = accessories.strip() or "Unit Only"
    item.intake_condition = intake_condition.strip() or "GOOD"
    if certificate_no.strip():
        item.certificate_no = certificate_no.strip()

    _recalc_order_financials(order)
    db.commit()

    target_url = redirect_to.strip() or f"/orders/{order_id}/bast"
    return RedirectResponse(
        url=f"{target_url}?success=Instrumen+berhasil+diperbarui",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/orders/{order_id}/items/{item_id}/delete")
def action_delete_order_item(
    order_id: int,
    item_id: int,
    redirect_to: str = Form(""),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    item = db.get(JobItem, item_id)
    if not item or item.order_id != order_id:
        raise HTTPException(status_code=404, detail="Item not found")

    order = (
        db.query(Order)
        .options(joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    db.delete(item)
    db.flush()
    if order:
        _recalc_order_financials(order)
    db.commit()

    target_url = redirect_to.strip() or f"/orders/{order_id}/bast"
    return RedirectResponse(
        url=f"{target_url}?success=Instrumen+berhasil+dihapus",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/orders/{order_id}/bast/save")
def page_bast_save(
    order_id: int,
    db: Session = Depends(get_db),
    items_json: str = Form(...),
) -> RedirectResponse:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items_data: list[dict[str, Any]] = json.loads(items_json)
    seq = _get_next_sequence(db, order_id)

    for item_data in items_data:
        qr_tag = _generate_qr_tag(order_id, seq)
        qty = int(item_data.get("qty") or 1)
        unit_price = int(item_data.get("unit_price") or 0)
        subcon_id = (
            int(item_data["subcontractor_id"])
            if item_data.get("subcontractor_id")
            else None
        )
        subcon_price = int(item_data.get("subcon_price") or 0)

        job_item = JobItem(
            order_id=order_id,
            qr_tag=qr_tag,
            instrument_name=item_data["instrument_name"],
            specification_desc=item_data.get("specification_desc") or None,
            brand=item_data.get("brand") or None,
            model=item_data.get("model") or None,
            serial_number=item_data["serial_number"],
            scope=Scope(item_data["scope"]),
            qty=qty,
            unit=item_data.get("unit") or "Unit",
            unit_price=unit_price,
            subcontractor_id=subcon_id,
            subcon_price=subcon_price,
            accessories=item_data.get("accessories") or "Unit Only",
            intake_condition=item_data.get("intake_condition") or "GOOD",
            status=JobStatus.RECEIVED,
        )
        sync_job_item_release(job_item, order.po_status)
        db.add(job_item)
        db.flush()
        if not job_item.certificate_no:
            job_item.certificate_no = generate_certificate_no(job_item.id)
        seq += 1

    if not order.received_date:
        order.received_date = date.today()

    _recalc_order_financials(order)
    db.commit()
    return RedirectResponse(url=f"/orders/{order_id}/bast", status_code=303)


@router.get("/orders/{order_id}/print-bast", response_class=HTMLResponse)
def page_print_bast(
    order_id: int, request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse(
        request=request,
        name="bast/print.html",
        context={
            "order": order,
            "items": order.job_items,
            "today": date.today(),
        },
    )


# --- REST API Endpoints ---


@router.get("/api/orders/{order_id}/items", response_model=list[JobItemRead])
def api_list_order_items(
    order_id: int, db: Session = Depends(get_db)
) -> list[JobItem]:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return (
        db.query(JobItem)
        .filter(JobItem.order_id == order_id)
        .order_by(JobItem.id.asc())
        .all()
    )


@router.post(
    "/api/orders/{order_id}/items",
    response_model=list[JobItemRead],
    status_code=201,
)
def api_add_order_items(
    order_id: int,
    payload: list[JobItemIntake],
    db: Session = Depends(get_db),
) -> list[JobItem]:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    created_items: list[JobItem] = []
    seq = _get_next_sequence(db, order_id)

    for intake in payload:
        qr_tag = _generate_qr_tag(order_id, seq)
        item = JobItem(
            order_id=order_id,
            qr_tag=qr_tag,
            instrument_name=intake.instrument_name,
            specification_desc=intake.specification_desc,
            brand=intake.brand,
            model=intake.model,
            serial_number=intake.serial_number,
            scope=intake.scope,
            qty=intake.qty,
            unit=intake.unit,
            unit_price=intake.unit_price,
            subcontractor_id=intake.subcontractor_id,
            subcon_price=intake.subcon_price,
            accessories=intake.accessories or "Unit Only",
            intake_condition=intake.intake_condition or "GOOD",
            master_equipment_id=intake.master_equipment_id,
            status=JobStatus.RECEIVED,
        )
        sync_job_item_release(item, order.po_status)
        db.add(item)
        db.flush()
        if not item.certificate_no:
            item.certificate_no = generate_certificate_no(item.id)
        created_items.append(item)
        seq += 1

    _recalc_order_financials(order)
    db.commit()
    for item in created_items:
        db.refresh(item)
    return created_items


@router.get("/api/job-items/{item_id}", response_model=JobItemRead)
def api_get_job_item(item_id: int, db: Session = Depends(get_db)) -> JobItem:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")
    return item


@router.patch("/api/job-items/{item_id}/status", response_model=JobItemRead)
def api_update_job_item_status(
    item_id: int,
    payload: JobItemStatusUpdate,
    db: Session = Depends(get_db),
) -> JobItem:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    order = db.get(Order, item.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    item.status = payload.status
    if payload.assigned_tech is not None:
        item.assigned_tech = payload.assigned_tech
    if payload.certificate_no is not None:
        item.certificate_no = payload.certificate_no
    elif item.status in (JobStatus.CERT_READY, JobStatus.DELIVERED) and not item.certificate_no:
        item.certificate_no = generate_certificate_no(item.id)

    # Admin Hold Logic strictly applied here:
    sync_job_item_release(item, order.po_status)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/api/job-items/{item_id}", status_code=204)
def api_delete_job_item(item_id: int, db: Session = Depends(get_db)) -> None:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")
    order = db.get(Order, item.order_id)
    db.delete(item)
    if order:
        _recalc_order_financials(order)
    db.commit()
