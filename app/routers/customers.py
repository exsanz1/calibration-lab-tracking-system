from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.templates_config import templates

router = APIRouter()


# --- API Endpoints ---

@router.get("/api/customers", response_model=list[CustomerRead])
def api_list_customers(db: Session = Depends(get_db)) -> list[Customer]:
    return db.query(Customer).order_by(Customer.company_name).all()


@router.get("/api/customers/{customer_id}", response_model=CustomerRead)
def api_get_customer(customer_id: int, db: Session = Depends(get_db)) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/api/customers", response_model=CustomerRead, status_code=201)
def api_create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.put("/api/customers/{customer_id}", response_model=CustomerRead)
def api_update_customer(
    customer_id: int, payload: CustomerCreate, db: Session = Depends(get_db)
) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump().items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.patch("/api/customers/{customer_id}", response_model=CustomerRead)
def api_partial_update_customer(
    customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)
) -> Customer:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/api/customers/{customer_id}", status_code=204)
def api_delete_customer(customer_id: int, db: Session = Depends(get_db)) -> None:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()


# --- HTML Page Endpoints ---

@router.get("/customers", response_class=HTMLResponse)
def page_customers(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    customers = db.query(Customer).order_by(Customer.company_name).all()
    return templates.TemplateResponse(
        request=request,
        name="customers/list.html",
        context={"customers": customers},
    )


@router.get("/customers/create", response_class=HTMLResponse)
def page_customer_create(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="customers/form.html",
        context={"customer": None},
    )


@router.get("/customers/{customer_id}/edit", response_class=HTMLResponse)
def page_customer_edit(customer_id: int, request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return templates.TemplateResponse(
        request=request,
        name="customers/form.html",
        context={"customer": customer},
    )


@router.post("/customers/save")
def page_customer_save(
    db: Session = Depends(get_db),
    customer_id: int = Form(0),
    company_name: str = Form(...),
    pic_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    address: str = Form(""),
) -> RedirectResponse:
    if customer_id:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer.company_name = company_name
        customer.pic_name = pic_name
        customer.phone = phone
        customer.email = email or None
        customer.address = address or None
    else:
        customer = Customer(
            company_name=company_name,
            pic_name=pic_name,
            phone=phone,
            email=email or None,
            address=address or None,
        )
        db.add(customer)
    db.commit()
    return RedirectResponse(url="/customers", status_code=303)


@router.post("/customers/{customer_id}/delete")
def page_customer_delete(customer_id: int, db: Session = Depends(get_db)) -> RedirectResponse:
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    db.delete(customer)
    db.commit()
    return RedirectResponse(url="/customers", status_code=303)
