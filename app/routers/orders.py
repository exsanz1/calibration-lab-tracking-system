from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus
from app.models.order import InvoiceStatus, Order, POStatus, ServiceType
from app.models.po_out import PurchaseOrderOut
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate
from app.services.admin_hold import sync_order_job_items_release
from app.services.doc_generator import (
    generate_ba_docx,
    generate_invoice_docx,
    generate_ordersheet_xlsx,
    generate_penawaran_docx,
    generate_tt_docx,
)
from app.services.number_generator import (
    generate_bast_no,
    generate_invoice_no,
    generate_ordersheet_no,
    generate_quotation_no,
    generate_tt_no,
)
from app.templates_config import templates

router = APIRouter()


def recalc_order_financials(order: Order) -> None:
    """Recalculate order subtotal, PPN, and grand total from job items."""
    subtot = sum(it.unit_price * it.qty for it in order.job_items)
    ppn = int(subtot * (order.ppn_percent / 100.0))
    order.subtotal = subtot
    order.ppn_amount = ppn
    order.grand_total = subtot + ppn


# ==========================================
# REST API ENDPOINTS
# ==========================================


@router.get("/api/orders", response_model=list[OrderRead])
def api_list_orders(db: Session = Depends(get_db)) -> list[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.customer))
        .order_by(Order.id.desc())
        .all()
    )


@router.get("/api/orders/{order_id}", response_model=OrderRead)
def api_get_order(order_id: int, db: Session = Depends(get_db)) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/api/orders", response_model=OrderRead, status_code=201)
def api_create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> Order:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="Customer does not exist")
    order = Order(**payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.put("/api/orders/{order_id}", response_model=OrderRead)
def api_update_order(
    order_id: int, payload: OrderCreate, db: Session = Depends(get_db)
) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.job_items), joinedload(Order.customer))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for key, value in payload.model_dump().items():
        setattr(order, key, value)
    recalc_order_financials(order)
    sync_order_job_items_release(order)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/api/orders/{order_id}", response_model=OrderRead)
def api_partial_update_order(
    order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)
) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.job_items), joinedload(Order.customer))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, key, value)
    recalc_order_financials(order)
    sync_order_job_items_release(order)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/api/orders/{order_id}", status_code=204)
def api_delete_order(order_id: int, db: Session = Depends(get_db)) -> None:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()


# ==========================================
# DOCUMENT GENERATION & DOWNLOAD ENDPOINTS
# ==========================================


@router.get("/orders/{order_id}/docs/penawaran")
def download_penawaran_docx(order_id: int, db: Session = Depends(get_db)) -> Response:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    recalc_order_financials(order)
    content = generate_penawaran_docx(order)
    safe_q = (order.quotation_no or f"Order_{order.id}").replace("/", "_")
    filename = f"Penawaran_{safe_q}.docx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/docs/ordersheet")
def download_ordersheet_xlsx(order_id: int, db: Session = Depends(get_db)) -> Response:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    content = generate_ordersheet_xlsx(order)
    safe_no = (order.ordersheet_no or f"Order_{order.id}").replace(".", "_")
    filename = f"OrderSheet_{safe_no}.xlsx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/docs/tt")
def download_tt_docx(order_id: int, db: Session = Depends(get_db)) -> Response:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    content = generate_tt_docx(order)
    safe_no = (order.tt_no or f"TT_{order.id}").replace("/", "_")
    filename = f"TandaTerima_{safe_no}.docx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/docs/ba")
def download_ba_docx(order_id: int, db: Session = Depends(get_db)) -> Response:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    content = generate_ba_docx(order)
    safe_no = (order.bast_no or f"BA_{order.id}").replace("/", "_")
    filename = f"BeritaAcara_{safe_no}.docx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/orders/{order_id}/docs/invoice")
def download_invoice_docx(order_id: int, db: Session = Depends(get_db)) -> Response:
    order = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    recalc_order_financials(order)
    content = generate_invoice_docx(order)
    safe_no = (order.invoice_no or f"INV_{order.id}").replace("/", "_")
    filename = f"Invoice_{safe_no}.docx"

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ==========================================
# WORKFLOW NUMBER GENERATION SHORTCUTS
# ==========================================


@router.post("/orders/{order_id}/gen/quotation")
@router.post("/orders/{order_id}/actions/gen-quotation")
def action_gen_quotation(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    q_date = order.quotation_date or date.today()
    if not order.quotation_no:
        order.quotation_no = generate_quotation_no(order.id, q_date)
    order.quotation_date = q_date
    recalc_order_financials(order)
    db.commit()

    return RedirectResponse(
        url=f"/orders/{order_id}?success=Nomor+penawaran+berhasil+diterbitkan",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/orders/{order_id}/gen/ordersheet")
@router.post("/orders/{order_id}/actions/gen-ordersheet")
def action_gen_ordersheet(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.ordersheet_no:
        order.ordersheet_no = generate_ordersheet_no(order.id, order.received_date or date.today())
    db.commit()

    return RedirectResponse(
        url=f"/orders/{order_id}?success=Nomor+ordersheet+berhasil+diterbitkan",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/orders/{order_id}/gen/bast")
@router.post("/orders/{order_id}/actions/gen-bast-tt")
def action_gen_bast(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Guardrails check
    if order.po_status != POStatus.RECEIVED:
        return RedirectResponse(
            url=f"/orders/{order_id}?error=BAST+tidak+dapat+diterbitkan:+Status+PO+masih+PENDING",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    if not order.job_items:
        return RedirectResponse(
            url=f"/orders/{order_id}?error=BAST+tidak+dapat+diterbitkan:+Belum+ada+instrumen+terdaftar",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    for it in order.job_items:
        if it.status not in (JobStatus.CERT_READY, JobStatus.DELIVERED):
            return RedirectResponse(
                url=f"/orders/{order_id}?error=BAST+tidak+dapat+diterbitkan:+Instrumen+{it.instrument_name}+belum+selesai",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    today = date.today()
    if not order.bast_no:
        order.bast_no = generate_bast_no(order.id, today)
    if not order.tt_no:
        order.tt_no = generate_tt_no(order.id, today)
    if not order.returned_date:
        order.returned_date = today

    db.commit()
    return RedirectResponse(
        url=f"/orders/{order_id}?success=Berita+Acara+dan+Tanda+Terima+berhasil+diterbitkan",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/orders/{order_id}/gen/invoice")
@router.post("/orders/{order_id}/actions/gen-invoice")
def action_gen_invoice(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if not order.bast_no:
        return RedirectResponse(
            url=f"/orders/{order_id}?error=Invoice+tidak+dapat+diterbitkan:+BAST+belum+dibuat",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    today = date.today()
    if not order.invoice_no:
        order.invoice_no = generate_invoice_no(order.id, today)
    order.invoice_date = today
    order.invoice_status = InvoiceStatus.INVOICED
    recalc_order_financials(order)
    db.commit()

    return RedirectResponse(
        url=f"/orders/{order_id}?success=Invoice+berhasil+diterbitkan",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/orders/{order_id}/recalc")
@router.post("/orders/{order_id}/actions/recalc")
def action_recalc_financials(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = (
        db.query(Order)
        .options(joinedload(Order.job_items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    recalc_order_financials(order)
    db.commit()
    return RedirectResponse(
        url=f"/orders/{order_id}?success=Kalkulasi+keuangan+berhasil+diperbarui",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# ==========================================
# HTML PAGE ENDPOINTS
# ==========================================


@router.get("/orders", response_class=HTMLResponse)
def page_orders(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    orders = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .order_by(Order.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="orders/list.html",
        context={"orders": orders},
    )


@router.get("/orders/create", response_class=HTMLResponse)
def page_order_create(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    customers = db.query(Customer).order_by(Customer.company_name).all()
    return templates.TemplateResponse(
        request=request,
        name="orders/form.html",
        context={
            "order": None,
            "customers": customers,
            "po_statuses": list(POStatus),
            "service_types": list(ServiceType),
            "invoice_statuses": list(InvoiceStatus),
            "today_date": date.today().isoformat(),
        },
    )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def page_order_detail(
    order_id: int,
    request: Request,
    success: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    order = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.job_items).joinedload(JobItem.subcontractor),
            joinedload(Order.purchase_orders_out).joinedload(PurchaseOrderOut.subcontractor),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    recalc_order_financials(order)
    db.commit()

    # Determine 7-stage workflow completion states:
    # 1. Penawaran
    stage_1 = bool(order.quotation_no)
    # 2. PO Masuk
    stage_2 = order.po_status == POStatus.RECEIVED
    # 3. Ordersheet
    stage_3 = bool(order.ordersheet_no)
    # 4. Penerimaan Alat
    stage_4 = bool(order.received_date) and len(order.job_items) > 0
    # 5. Pengerjaan Alat
    all_ready = (
        len(order.job_items) > 0
        and all(it.status in (JobStatus.CERT_READY, JobStatus.DELIVERED) for it in order.job_items)
    )
    stage_5 = all_ready
    # 6. Pengembalian Alat (TT + BA)
    stage_6 = bool(order.bast_no) and bool(order.tt_no)
    # 7. Invoice
    stage_7 = bool(order.invoice_no)

    # Current active step index (1-7)
    current_step = 1
    if stage_1:
        current_step = 2
    if stage_2:
        current_step = 3
    if stage_3:
        current_step = 4
    if stage_4:
        current_step = 5
    if stage_5:
        current_step = 6
    if stage_6:
        current_step = 7
    if stage_7:
        current_step = 8

    return templates.TemplateResponse(
        request=request,
        name="orders/detail.html",
        context={
            "order": order,
            "stages": [
                {"num": 1, "name": "Penawaran", "done": stage_1, "code": order.quotation_no},
                {"num": 2, "name": "PO Customer", "done": stage_2, "code": order.po_no or "Pending"},
                {"num": 3, "name": "Ordersheet", "done": stage_3, "code": order.ordersheet_no},
                {"num": 4, "name": "Penerimaan Alat", "done": stage_4, "code": f"{len(order.job_items)} Item"},
                {"num": 5, "name": "Pengerjaan Alat", "done": stage_5, "code": "Selesai" if stage_5 else "Proses"},
                {"num": 6, "name": "Pengembalian (TT+BA)", "done": stage_6, "code": order.bast_no},
                {"num": 7, "name": "Invoice", "done": stage_7, "code": order.invoice_no},
            ],
            "current_step": current_step,
            "success_msg": success,
            "error_msg": error,
        },
    )


@router.get("/orders/{order_id}/edit", response_class=HTMLResponse)
def page_order_edit(
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
    customers = db.query(Customer).order_by(Customer.company_name).all()
    return templates.TemplateResponse(
        request=request,
        name="orders/form.html",
        context={
            "order": order,
            "customers": customers,
            "po_statuses": list(POStatus),
            "service_types": list(ServiceType),
            "invoice_statuses": list(InvoiceStatus),
            "today_date": date.today().isoformat(),
        },
    )


@router.post("/orders/save")
def page_order_save(
    db: Session = Depends(get_db),
    order_id: int = Form(0),
    customer_id: int = Form(...),
    job_info: str = Form("Kalibrasi"),
    quotation_no: str = Form(""),
    quotation_date: str = Form(""),
    revision_no: str = Form("00"),
    notes: str = Form(""),
    po_no: str = Form(""),
    po_status: str = Form("PENDING"),
    service_type: str = Form(...),
    ordersheet_no: str = Form(""),
    received_date: str = Form(""),
    target_sla_date: str = Form(""),
    tt_no: str = Form(""),
    returned_date: str = Form(""),
    bast_no: str = Form(""),
    invoice_no: str = Form(""),
    invoice_date: str = Form(""),
    terms_pembayaran: str = Form("30 Hari"),
    invoice_status: str = Form("UNBILLED"),
) -> RedirectResponse:
    parsed_quotation_date = date.fromisoformat(quotation_date) if quotation_date else None
    parsed_received = date.fromisoformat(received_date) if received_date else None
    parsed_sla = date.fromisoformat(target_sla_date) if target_sla_date else None
    parsed_returned = date.fromisoformat(returned_date) if returned_date else None
    parsed_invoice_date = date.fromisoformat(invoice_date) if invoice_date else None

    if order_id:
        order = (
            db.query(Order)
            .options(joinedload(Order.job_items))
            .filter(Order.id == order_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        order.customer_id = customer_id
        order.job_info = job_info.strip() or "Kalibrasi"
        order.quotation_no = quotation_no.strip() or None
        order.quotation_date = parsed_quotation_date
        order.revision_no = revision_no.strip() or "00"
        order.notes = notes.strip()
        order.po_no = po_no.strip() or None
        order.po_status = POStatus(po_status)
        order.service_type = ServiceType(service_type)
        order.ordersheet_no = ordersheet_no.strip() or None
        order.received_date = parsed_received
        order.target_sla_date = parsed_sla
        order.tt_no = tt_no.strip() or None
        order.returned_date = parsed_returned
        order.bast_no = bast_no.strip() or None
        order.invoice_no = invoice_no.strip() or None
        order.invoice_date = parsed_invoice_date
        order.terms_pembayaran = terms_pembayaran.strip() or "30 Hari"
        order.invoice_status = InvoiceStatus(invoice_status)
        recalc_order_financials(order)
        sync_order_job_items_release(order)
    else:
        order = Order(
            customer_id=customer_id,
            job_info=job_info.strip() or "Kalibrasi",
            quotation_no=quotation_no.strip() or None,
            quotation_date=parsed_quotation_date,
            revision_no=revision_no.strip() or "00",
            notes=notes.strip(),
            po_no=po_no.strip() or None,
            po_status=POStatus(po_status),
            service_type=ServiceType(service_type),
            ordersheet_no=ordersheet_no.strip() or None,
            received_date=parsed_received,
            target_sla_date=parsed_sla,
            tt_no=tt_no.strip() or None,
            returned_date=parsed_returned,
            bast_no=bast_no.strip() or None,
            invoice_no=invoice_no.strip() or None,
            invoice_date=parsed_invoice_date,
            terms_pembayaran=terms_pembayaran.strip() or "30 Hari",
            invoice_status=InvoiceStatus(invoice_status),
        )
        db.add(order)
        db.flush()
        if not order.quotation_no:
            order.quotation_no = generate_quotation_no(order.id, parsed_quotation_date or date.today())
        if not order.ordersheet_no:
            order.ordersheet_no = generate_ordersheet_no(order.id, parsed_received or date.today())

    db.commit()
    return RedirectResponse(url=f"/orders/{order.id}", status_code=303)


@router.post("/orders/{order_id}/delete")
def page_order_delete(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=303)
