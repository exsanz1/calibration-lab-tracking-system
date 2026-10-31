from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.job_item import JobItem
from app.models.order import Order
from app.models.po_out import POOutStatus, PurchaseOrderOut
from app.models.subcontractor import Subcontractor
from app.schemas.po_out import POOutCreate, POOutRead, POOutUpdate
from app.services.doc_generator import generate_po_keluar_docx
from app.services.number_generator import generate_po_out_no
from app.templates_config import templates

router = APIRouter()


# ==========================================
# REST API ENDPOINTS
# ==========================================


@router.get("/api/po-out", response_model=list[POOutRead])
def api_list_po_out(
    db: Session = Depends(get_db),
) -> list[PurchaseOrderOut]:
    return (
        db.query(PurchaseOrderOut)
        .options(
            joinedload(PurchaseOrderOut.subcontractor),
            joinedload(PurchaseOrderOut.order),
            joinedload(PurchaseOrderOut.job_items),
        )
        .order_by(PurchaseOrderOut.id.desc())
        .all()
    )


@router.post(
    "/api/po-out",
    response_model=POOutRead,
    status_code=status.HTTP_201_CREATED,
)
def api_create_po_out(
    payload: POOutCreate, db: Session = Depends(get_db)
) -> PurchaseOrderOut:
    sub = db.get(Subcontractor, payload.subcontractor_id)
    if not sub:
        raise HTTPException(status_code=400, detail="Subcontractor not found")
    order = db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=400, detail="Order not found")

    po_out = PurchaseOrderOut(
        po_out_no=payload.po_out_no or generate_po_out_no(order.id, payload.po_date),
        subcontractor_id=payload.subcontractor_id,
        order_id=payload.order_id,
        job_info=payload.job_info or "Kalibrasi",
        po_date=payload.po_date,
        delivery_date=payload.delivery_date,
        vendor_quotation_no=payload.vendor_quotation_no or "-",
        notes=payload.notes or "",
        onsite_fee=payload.onsite_fee,
        status=POOutStatus.ISSUED,
    )
    db.add(po_out)
    db.flush()

    # Link items if provided
    items_to_calc = []
    if payload.item_ids:
        items = (
            db.query(JobItem)
            .filter(
                JobItem.id.in_(payload.item_ids),
                JobItem.order_id == payload.order_id,
            )
            .all()
        )
        for it in items:
            it.po_out_id = po_out.id
            it.subcontractor_id = payload.subcontractor_id
            items_to_calc.append(it)
    else:
        # Default all items of order assigned to this subcon
        items_to_calc = [
            it
            for it in order.job_items
            if it.subcontractor_id == payload.subcontractor_id
        ]
        for it in items_to_calc:
            it.po_out_id = po_out.id

    subtot = sum(
        (it.subcon_price if it.subcon_price > 0 else it.unit_price) * it.qty
        for it in items_to_calc
    ) + payload.onsite_fee
    ppn = int(subtot * 0.11)
    grand = subtot + ppn

    po_out.subtotal = subtot
    po_out.ppn_amount = ppn
    po_out.grand_total = grand

    db.commit()
    db.refresh(po_out)
    return po_out


# ==========================================
# HTML WEB VIEWS & ACTIONS
# ==========================================


@router.get("/po-out", response_class=HTMLResponse)
def page_po_out_index(
    request: Request,
    q: str | None = None,
    success: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    query = (
        db.query(PurchaseOrderOut)
        .options(
            joinedload(PurchaseOrderOut.subcontractor),
            joinedload(PurchaseOrderOut.order).joinedload(Order.customer),
            joinedload(PurchaseOrderOut.job_items),
        )
    )
    if q:
        pat = f"%{q.strip()}%"
        query = query.join(Subcontractor).filter(
            (PurchaseOrderOut.po_out_no.ilike(pat))
            | (Subcontractor.vendor_name.ilike(pat))
        )
    pos = query.order_by(PurchaseOrderOut.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="po_out/index.html",
        context={
            "pos": pos,
            "total_count": len(pos),
            "search_query": q or "",
            "success_msg": success,
            "error_msg": error,
        },
    )


@router.get("/po-out/create", response_class=HTMLResponse)
def page_po_out_create(
    request: Request,
    order_id: int | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    subs = db.query(Subcontractor).order_by(Subcontractor.vendor_name).all()
    orders = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .order_by(Order.id.desc())
        .limit(30)
        .all()
    )

    selected_order = db.get(Order, order_id) if order_id else None
    default_po_out_no = generate_po_out_no(
        selected_order.id if selected_order else (len(orders) + 1)
    )

    return templates.TemplateResponse(
        request=request,
        name="po_out/form.html",
        context={
            "is_edit": False,
            "po": None,
            "subcontractors": subs,
            "orders": orders,
            "selected_order": selected_order,
            "default_po_out_no": default_po_out_no,
            "today_date": date.today().isoformat(),
        },
    )


@router.post("/po-out", response_model=None)
def action_po_out_create(
    request: Request,
    subcontractor_id: int = Form(...),
    order_id: int = Form(...),
    po_out_no: str = Form(""),
    job_info: str = Form("Kalibrasi"),
    po_date: str = Form(""),
    delivery_date: str = Form(""),
    vendor_quotation_no: str = Form("-"),
    notes: str = Form(""),
    onsite_fee: int = Form(0),
    db: Session = Depends(get_db),
) -> Response:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=400, detail="Order not found")

    parsed_po_date = (
        date.fromisoformat(po_date.strip()) if po_date.strip() else date.today()
    )
    parsed_deliv_date = (
        date.fromisoformat(delivery_date.strip()) if delivery_date.strip() else None
    )

    clean_po_no = po_out_no.strip() or generate_po_out_no(order.id, parsed_po_date)

    po = PurchaseOrderOut(
        po_out_no=clean_po_no,
        subcontractor_id=subcontractor_id,
        order_id=order_id,
        job_info=job_info.strip() or "Kalibrasi",
        po_date=parsed_po_date,
        delivery_date=parsed_deliv_date,
        vendor_quotation_no=vendor_quotation_no.strip() or "-",
        notes=notes.strip(),
        onsite_fee=onsite_fee,
        status=POOutStatus.ISSUED,
    )
    db.add(po)
    db.flush()

    # Link items from this order
    subtot = onsite_fee
    for item in order.job_items:
        item.po_out_id = po.id
        item.subcontractor_id = subcontractor_id
        price = item.subcon_price if item.subcon_price > 0 else item.unit_price
        subtot += price * item.qty

    ppn = int(subtot * 0.11)
    po.subtotal = subtot
    po.ppn_amount = ppn
    po.grand_total = subtot + ppn

    db.commit()
    return RedirectResponse(
        url=f"/po-out/{po.id}?success=PO+Keluar+berhasil+diterbitkan",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/po-out/{id}", response_class=HTMLResponse)
def page_po_out_detail(
    id: int,
    request: Request,
    success: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    po = (
        db.query(PurchaseOrderOut)
        .options(
            joinedload(PurchaseOrderOut.subcontractor),
            joinedload(PurchaseOrderOut.order).joinedload(Order.customer),
            joinedload(PurchaseOrderOut.job_items),
        )
        .filter(PurchaseOrderOut.id == id)
        .first()
    )
    if not po:
        raise HTTPException(status_code=404, detail="PO Keluar not found")

    return templates.TemplateResponse(
        request=request,
        name="po_out/detail.html",
        context={"po": po, "success_msg": success},
    )


@router.get("/po-out/{id}/doc")
def download_po_out_docx(id: int, db: Session = Depends(get_db)) -> Response:
    po = (
        db.query(PurchaseOrderOut)
        .options(
            joinedload(PurchaseOrderOut.subcontractor),
            joinedload(PurchaseOrderOut.order).joinedload(Order.customer),
            joinedload(PurchaseOrderOut.job_items),
        )
        .filter(PurchaseOrderOut.id == id)
        .first()
    )
    if not po:
        raise HTTPException(status_code=404, detail="PO Keluar not found")

    doc_bytes = generate_po_keluar_docx(po)
    safe_name = po.po_out_no.replace("/", "_").replace(" ", "_")
    filename = f"PO_Keluar_{safe_name}.docx"

    return Response(
        content=doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
