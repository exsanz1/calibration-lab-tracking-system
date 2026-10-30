from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus
from app.models.order import Order, POStatus
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def page_dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    total_customers = db.query(Customer).count()
    total_orders = db.query(Order).count()
    total_items = db.query(JobItem).count()

    pending_po_count = (
        db.query(Order).filter(Order.po_status == POStatus.PENDING).count()
    )

    cert_ready_items = (
        db.query(JobItem)
        .options(joinedload(JobItem.order))
        .filter(JobItem.status == JobStatus.CERT_READY)
        .all()
    )

    held_items_count = sum(1 for item in cert_ready_items if not item.release_allowed)
    released_items_count = sum(1 for item in cert_ready_items if item.release_allowed)

    recent_orders = (
        db.query(Order)
        .options(joinedload(Order.customer), joinedload(Order.job_items))
        .order_by(Order.id.desc())
        .limit(6)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "total_customers": total_customers,
            "total_orders": total_orders,
            "total_items": total_items,
            "pending_po_count": pending_po_count,
            "held_items_count": held_items_count,
            "released_items_count": released_items_count,
            "recent_orders": recent_orders,
        },
    )
