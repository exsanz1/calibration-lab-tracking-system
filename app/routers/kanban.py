from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.customer import Customer
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import Order, ServiceType
from app.templates_config import templates

router = APIRouter()

# The 6 visual columns on the Kanban board (HOLD_ADMIN is not a column;
# it displays in CERT_READY with an amber-600 "Hold Admin (PO Pending)" badge)
KANBAN_COLUMNS: list[JobStatus] = [
    JobStatus.RECEIVED,
    JobStatus.QUEUED,
    JobStatus.CALIBRATING,
    JobStatus.REVIEW,
    JobStatus.CERT_READY,
    JobStatus.DELIVERED,
]


@router.get("/kanban", response_class=HTMLResponse)
def page_kanban(
    request: Request,
    db: Session = Depends(get_db),
    scope: str = "",
    assigned_tech: str = "",
    service_type: str = "",
) -> HTMLResponse:
    # Base query with eager loading
    query = (
        db.query(JobItem)
        .join(JobItem.order)
        .join(Order.customer)
        .options(
            joinedload(JobItem.order).joinedload(Order.customer),
            joinedload(JobItem.master_equipment),
        )
    )

    # Apply filters
    if scope:
        try:
            scope_enum = Scope(scope)
            query = query.filter(JobItem.scope == scope_enum)
        except ValueError:
            pass

    if assigned_tech:
        query = query.filter(JobItem.assigned_tech == assigned_tech)

    if service_type:
        try:
            service_enum = ServiceType(service_type)
            query = query.filter(Order.service_type == service_enum)
        except ValueError:
            pass

    all_items = query.order_by(JobItem.id.desc()).all()

    # Group items by Kanban column
    columns_data: dict[str, list[JobItem]] = {col.value: [] for col in KANBAN_COLUMNS}

    for item in all_items:
        if item.status == JobStatus.HOLD_ADMIN:
            # Plan rule: Do NOT render HOLD_ADMIN as a separate column;
            # place under CERT_READY with amber Hold Admin badge
            columns_data[JobStatus.CERT_READY.value].append(item)
        elif item.status.value in columns_data:
            columns_data[item.status.value].append(item)

    # Plan rule: Limit DELIVERED column query to latest 30 items
    delivered_total_count = len(columns_data[JobStatus.DELIVERED.value])
    columns_data[JobStatus.DELIVERED.value] = columns_data[JobStatus.DELIVERED.value][:30]

    # Gather distinct technicians for filter dropdown
    technicians_raw = (
        db.query(JobItem.assigned_tech)
        .filter(JobItem.assigned_tech.isnot(None), JobItem.assigned_tech != "")
        .distinct()
        .all()
    )
    technicians = sorted([t[0] for t in technicians_raw if t[0]])

    return templates.TemplateResponse(
        request=request,
        name="kanban/board.html",
        context={
            "columns": KANBAN_COLUMNS,
            "columns_data": columns_data,
            "delivered_total_count": delivered_total_count,
            "scopes": list(Scope),
            "service_types": list(ServiceType),
            "technicians": technicians,
            "filter_scope": scope,
            "filter_tech": assigned_tech,
            "filter_service": service_type,
        },
    )


@router.get("/kanban/archive", response_class=HTMLResponse)
def page_kanban_archive(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    scope: str = "",
) -> HTMLResponse:
    """Searchable archive table for all delivered instruments."""
    query = (
        db.query(JobItem)
        .options(
            joinedload(JobItem.order).joinedload(Order.customer),
            joinedload(JobItem.master_equipment),
        )
        .filter(JobItem.status == JobStatus.DELIVERED)
    )

    if scope:
        try:
            scope_enum = Scope(scope)
            query = query.filter(JobItem.scope == scope_enum)
        except ValueError:
            pass

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.join(JobItem.order).join(Order.customer).filter(
            (JobItem.qr_tag.ilike(search_pattern))
            | (JobItem.instrument_name.ilike(search_pattern))
            | (JobItem.serial_number.ilike(search_pattern))
            | (JobItem.certificate_no.ilike(search_pattern))
            | (Customer.company_name.ilike(search_pattern))
        )

    archived_items = query.order_by(JobItem.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="kanban/archive.html",
        context={
            "items": archived_items,
            "scopes": list(Scope),
            "search_query": q,
            "filter_scope": scope,
        },
    )


# --- Quick Status QR Scan Page ---

@router.get("/scan", response_class=HTMLResponse)
def page_scan_index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    recent_items = (
        db.query(JobItem)
        .options(joinedload(JobItem.order))
        .order_by(JobItem.id.desc())
        .limit(10)
        .all()
    )
    return templates.TemplateResponse(
        request=request,
        name="kanban/scan_index.html",
        context={"recent_items": recent_items},
    )


@router.get("/scan/{qr_tag}", response_class=HTMLResponse)
def page_scan_detail(
    qr_tag: str, request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Mobile-friendly quick status scan page when scanning physical QR code."""
    item = (
        db.query(JobItem)
        .options(
            joinedload(JobItem.order).joinedload(Order.customer),
            joinedload(JobItem.master_equipment),
        )
        .filter(JobItem.qr_tag == qr_tag.strip())
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Instrument with QR Tag '{qr_tag}' not found in database.",
        )

    active_masters = (
        db.query(MasterEquipment)
        .filter(
            MasterEquipment.scope == item.scope,
            MasterEquipment.status == EquipmentStatus.ACTIVE,
        )
        .order_by(MasterEquipment.name)
        .all()
    )

    all_statuses = [
        JobStatus.RECEIVED,
        JobStatus.QUEUED,
        JobStatus.CALIBRATING,
        JobStatus.REVIEW,
        JobStatus.CERT_READY,
        JobStatus.DELIVERED,
    ]

    return templates.TemplateResponse(
        request=request,
        name="kanban/scan_detail.html",
        context={
            "item": item,
            "order": item.order,
            "active_masters": active_masters,
            "statuses": all_statuses,
        },
    )

