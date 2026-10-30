from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.customer import Customer
from app.models.order import InvoiceStatus, Order, POStatus, ServiceType
from app.schemas.order import OrderCreate, OrderDetailRead, OrderRead, OrderUpdate
from app.services.admin_hold import sync_order_job_items_release
from app.templates_config import templates

router = APIRouter()


# --- API Endpoints ---

@router.get("/api/orders", response_model=list[OrderRead])
def api_list_orders(db: Session = Depends(get_db)) -> list[Order]:
    return (
        db.query(Order)
        .options(joinedload(Order.customer))
        .order_by(Order.id.desc())
        .all()
    )


@router.get("/api/orders/{order_id}", response_model=OrderDetailRead)
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


# --- HTML Page Endpoints ---

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
        },
    )


@router.get("/orders/{order_id}/edit", response_class=HTMLResponse)
def page_order_edit(
    order_id: int, request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    order = db.get(Order, order_id)
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
        },
    )


@router.post("/orders/save")
def page_order_save(
    db: Session = Depends(get_db),
    order_id: int = Form(0),
    customer_id: int = Form(...),
    quotation_no: str = Form(""),
    po_no: str = Form(""),
    po_status: str = Form("PENDING"),
    service_type: str = Form(...),
    bast_no: str = Form(""),
    received_date: str = Form(""),
    target_sla_date: str = Form(""),
    invoice_status: str = Form("UNBILLED"),
) -> RedirectResponse:
    parsed_received = date.fromisoformat(received_date) if received_date else None
    parsed_sla = date.fromisoformat(target_sla_date) if target_sla_date else None

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
        order.quotation_no = quotation_no or None
        order.po_no = po_no or None
        order.po_status = POStatus(po_status)
        order.service_type = ServiceType(service_type)
        order.bast_no = bast_no or None
        order.received_date = parsed_received
        order.target_sla_date = parsed_sla
        order.invoice_status = InvoiceStatus(invoice_status)
        sync_order_job_items_release(order)
    else:
        order = Order(
            customer_id=customer_id,
            quotation_no=quotation_no or None,
            po_no=po_no or None,
            po_status=POStatus(po_status),
            service_type=ServiceType(service_type),
            bast_no=bast_no or None,
            received_date=parsed_received,
            target_sla_date=parsed_sla,
            invoice_status=InvoiceStatus(invoice_status),
        )
        db.add(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=303)


@router.post("/orders/{order_id}/delete")
def page_order_delete(order_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return RedirectResponse(url="/orders", status_code=303)
