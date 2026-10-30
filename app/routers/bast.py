from __future__ import annotations

import json
import re
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.order import Order
from app.schemas.job_item import (
    JobItemIntake,
    JobItemRead,
    JobItemStatusUpdate,
)
from app.services.admin_hold import sync_job_item_release
from app.templates_config import templates

router = APIRouter()


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
        .filter(JobItem.order_id == order_id)
        .order_by(JobItem.id.asc())
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="bast/form.html",
        context={
            "order": order,
            "existing_items": existing_items,
            "scopes": list(Scope),
        },
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

    items_data: list[dict[str, str]] = json.loads(items_json)
    seq = _get_next_sequence(db, order_id)

    for item_data in items_data:
        qr_tag = _generate_qr_tag(order_id, seq)
        job_item = JobItem(
            order_id=order_id,
            qr_tag=qr_tag,
            instrument_name=item_data["instrument_name"],
            brand=item_data.get("brand") or None,
            model=item_data.get("model") or None,
            serial_number=item_data["serial_number"],
            scope=Scope(item_data["scope"]),
            accessories=item_data.get("accessories") or "Unit Only",
            intake_condition=item_data.get("intake_condition") or "GOOD",
            status=JobStatus.RECEIVED,
        )
        sync_job_item_release(job_item, order.po_status)
        db.add(job_item)
        seq += 1

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
            brand=intake.brand,
            model=intake.model,
            serial_number=intake.serial_number,
            scope=intake.scope,
            accessories=intake.accessories or "Unit Only",
            intake_condition=intake.intake_condition or "GOOD",
            master_equipment_id=intake.master_equipment_id,
            status=JobStatus.RECEIVED,
        )
        sync_job_item_release(item, order.po_status)
        db.add(item)
        created_items.append(item)
        seq += 1

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
    db.delete(item)
    db.commit()
