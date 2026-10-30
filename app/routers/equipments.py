from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_item import JobItem, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.schemas.master_equipment import (
    MasterEquipmentCreate,
    MasterEquipmentRead,
    MasterEquipmentUpdate,
)
from app.services.equipment_status import (
    get_equipment_alert_info,
    sync_and_evaluate_equipment_status,
)
from app.templates_config import templates

router = APIRouter()


# ==========================================
# REST API ENDPOINTS
# ==========================================


@router.get("/api/master-equipments", response_model=list[MasterEquipmentRead])
def api_list_master_equipments(
    scope: Scope | None = None,
    status_filter: EquipmentStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
) -> list[MasterEquipment]:
    """List all master equipment standards with real-time status evaluation."""
    sync_and_evaluate_equipment_status(db)
    query = db.query(MasterEquipment)
    if scope:
        query = query.filter(MasterEquipment.scope == scope)
    if status_filter:
        query = query.filter(MasterEquipment.status == status_filter)
    return query.order_by(MasterEquipment.due_date.asc().nulls_last()).all()


@router.post(
    "/api/master-equipments",
    response_model=MasterEquipmentRead,
    status_code=status.HTTP_201_CREATED,
)
def api_create_master_equipment(
    payload: MasterEquipmentCreate, db: Session = Depends(get_db)
) -> MasterEquipment:
    """Create a new master calibration equipment."""
    existing = (
        db.query(MasterEquipment)
        .filter(MasterEquipment.serial_number == payload.serial_number)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Master equipment with serial number '{payload.serial_number}' already exists.",
        )

    eq = MasterEquipment(
        name=payload.name,
        serial_number=payload.serial_number,
        scope=payload.scope,
        last_cal_date=payload.last_cal_date,
        due_date=payload.due_date,
        traceability_body=payload.traceability_body,
        status=payload.status,
    )
    db.add(eq)
    db.commit()
    db.refresh(eq)

    sync_and_evaluate_equipment_status(db)
    db.refresh(eq)
    return eq


@router.get("/api/master-equipments/{id}", response_model=MasterEquipmentRead)
def api_get_master_equipment(
    id: int, db: Session = Depends(get_db)
) -> MasterEquipment:
    """Get single master equipment by ID."""
    sync_and_evaluate_equipment_status(db)
    eq = db.get(MasterEquipment, id)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master equipment not found",
        )
    return eq


@router.put("/api/master-equipments/{id}", response_model=MasterEquipmentRead)
def api_update_master_equipment(
    id: int, payload: MasterEquipmentUpdate, db: Session = Depends(get_db)
) -> MasterEquipment:
    """Update master equipment fields."""
    eq = db.get(MasterEquipment, id)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master equipment not found",
        )

    if payload.serial_number and payload.serial_number != eq.serial_number:
        existing = (
            db.query(MasterEquipment)
            .filter(
                MasterEquipment.serial_number == payload.serial_number,
                MasterEquipment.id != id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Serial number '{payload.serial_number}' already in use.",
            )
        eq.serial_number = payload.serial_number

    if payload.name is not None:
        eq.name = payload.name
    if payload.scope is not None:
        eq.scope = payload.scope
    if payload.last_cal_date is not None:
        eq.last_cal_date = payload.last_cal_date
    if payload.due_date is not None:
        eq.due_date = payload.due_date
    if payload.traceability_body is not None:
        eq.traceability_body = payload.traceability_body
    if payload.status is not None:
        eq.status = payload.status

    db.commit()
    sync_and_evaluate_equipment_status(db)
    db.refresh(eq)
    return eq


@router.delete("/api/master-equipments/{id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_master_equipment(
    id: int, db: Session = Depends(get_db)
) -> None:
    """Delete master equipment. Fails if referenced by any JobItem."""
    eq = db.get(MasterEquipment, id)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master equipment not found",
        )

    linked_count = (
        db.query(JobItem).filter(JobItem.master_equipment_id == id).count()
    )
    if linked_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot delete master equipment '{eq.name}': it is linked to {linked_count} "
                "job calibration item(s) for ISO/IEC 17025 traceability integrity."
            ),
        )

    db.delete(eq)
    db.commit()


# ==========================================
# HTML WEB VIEWS & FORMS
# ==========================================


@router.get("/equipments", response_class=HTMLResponse)
def page_equipments_index(
    request: Request,
    scope: Scope | None = None,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = None,
    error: str | None = None,
    success: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Master equipments registry table with real-time expiration badges & filter bar."""
    all_equipments = sync_and_evaluate_equipment_status(db)

    # Compute overall metric counts
    total_count = len(all_equipments)
    active_count = 0
    expired_count = 0
    in_cal_count = 0
    critical_count = 0
    warning_count = 0

    today = date.today()
    for eq in all_equipments:
        info = get_equipment_alert_info(eq, today)
        level = info["alert_level"]
        if level == "EXPIRED":
            expired_count += 1
        elif level == "IN_CALIBRATION":
            in_cal_count += 1
        elif level == "CRITICAL":
            critical_count += 1
            active_count += 1
        elif level == "WARNING":
            warning_count += 1
            active_count += 1
        else:
            active_count += 1

    # Filtered list for display
    query = db.query(MasterEquipment)
    if scope:
        query = query.filter(MasterEquipment.scope == scope)
    if status_filter and status_filter != "ALL":
        try:
            enum_status = EquipmentStatus(status_filter)
            query = query.filter(MasterEquipment.status == enum_status)
        except ValueError:
            pass

    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            (MasterEquipment.name.ilike(search_pattern))
            | (MasterEquipment.serial_number.ilike(search_pattern))
            | (MasterEquipment.traceability_body.ilike(search_pattern))
        )

    displayed_equipments = query.order_by(MasterEquipment.due_date.asc().nulls_last()).all()

    # Decorate with alert info
    decorated_list: list[dict[str, Any]] = []
    for eq in displayed_equipments:
        alert_info = get_equipment_alert_info(eq, today)
        decorated_list.append({
            "item": eq,
            "alert": alert_info,
        })

    return templates.TemplateResponse(
        request=request,
        name="equipments/index.html",
        context={
            "equipments": decorated_list,
            "total_count": total_count,
            "active_count": active_count,
            "expired_count": expired_count,
            "in_cal_count": in_cal_count,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "scopes": list(Scope),
            "statuses": list(EquipmentStatus),
            "filter_scope": scope.value if scope else "",
            "filter_status": status_filter or "",
            "search_query": q or "",
            "error_msg": error,
            "success_msg": success,
        },
    )


@router.get("/equipments/create", response_class=HTMLResponse)
def page_equipments_create(
    request: Request, error: str | None = None
) -> HTMLResponse:
    """Form to register a new master calibration equipment."""
    return templates.TemplateResponse(
        request=request,
        name="equipments/form.html",
        context={
            "is_edit": False,
            "equipment": None,
            "scopes": list(Scope),
            "statuses": list(EquipmentStatus),
            "error_msg": error,
        },
    )


@router.post("/equipments", response_model=None)
def action_equipments_create(
    request: Request,
    name: str = Form(...),
    serial_number: str = Form(...),
    scope: Scope = Form(...),
    last_cal_date: str = Form(""),
    due_date: str = Form(""),
    traceability_body: str = Form(""),
    equipment_status: EquipmentStatus = Form(EquipmentStatus.ACTIVE, alias="status"),
    db: Session = Depends(get_db),
) -> Response:
    """Handle creation form submit."""
    existing = (
        db.query(MasterEquipment)
        .filter(MasterEquipment.serial_number == serial_number.strip())
        .first()
    )
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="equipments/form.html",
            context={
                "is_edit": False,
                "equipment": None,
                "scopes": list(Scope),
                "statuses": list(EquipmentStatus),
                "error_msg": f"Serial number '{serial_number}' is already registered.",
                "form_data": {
                    "name": name,
                    "serial_number": serial_number,
                    "scope": scope.value,
                    "last_cal_date": last_cal_date,
                    "due_date": due_date,
                    "traceability_body": traceability_body,
                    "status": equipment_status.value,
                },
            },
        )

    parsed_last_cal: date | None = None
    if last_cal_date.strip():
        try:
            parsed_last_cal = date.fromisoformat(last_cal_date.strip())
        except ValueError:
            pass

    parsed_due: date | None = None
    if due_date.strip():
        try:
            parsed_due = date.fromisoformat(due_date.strip())
        except ValueError:
            pass

    eq = MasterEquipment(
        name=name.strip(),
        serial_number=serial_number.strip(),
        scope=scope,
        last_cal_date=parsed_last_cal,
        due_date=parsed_due,
        traceability_body=traceability_body.strip() if traceability_body.strip() else None,
        status=equipment_status,
    )
    db.add(eq)
    db.commit()

    sync_and_evaluate_equipment_status(db)
    return RedirectResponse(
        url="/equipments?success=Master+equipment+registered+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/equipments/{id}/edit", response_class=HTMLResponse)
def page_equipments_edit(
    id: int, request: Request, error: str | None = None, db: Session = Depends(get_db)
) -> HTMLResponse:
    """Form to edit an existing master equipment."""
    sync_and_evaluate_equipment_status(db)
    eq = db.get(MasterEquipment, id)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master equipment not found",
        )

    return templates.TemplateResponse(
        request=request,
        name="equipments/form.html",
        context={
            "is_edit": True,
            "equipment": eq,
            "scopes": list(Scope),
            "statuses": list(EquipmentStatus),
            "error_msg": error,
        },
    )


@router.post("/equipments/{id}/edit", response_model=None)
def action_equipments_edit(
    id: int,
    request: Request,
    name: str = Form(...),
    serial_number: str = Form(...),
    scope: Scope = Form(...),
    last_cal_date: str = Form(""),
    due_date: str = Form(""),
    traceability_body: str = Form(""),
    equipment_status: EquipmentStatus = Form(..., alias="status"),
    db: Session = Depends(get_db),
) -> Response:
    """Handle edit form submit."""
    eq = db.get(MasterEquipment, id)
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master equipment not found",
        )

    clean_sn = serial_number.strip()
    if clean_sn != eq.serial_number:
        existing = (
            db.query(MasterEquipment)
            .filter(
                MasterEquipment.serial_number == clean_sn,
                MasterEquipment.id != id,
            )
            .first()
        )
        if existing:
            return templates.TemplateResponse(
                request=request,
                name="equipments/form.html",
                context={
                    "is_edit": True,
                    "equipment": eq,
                    "scopes": list(Scope),
                    "statuses": list(EquipmentStatus),
                    "error_msg": f"Serial number '{clean_sn}' is already in use by another equipment.",
                },
            )

    parsed_last_cal: date | None = None
    if last_cal_date.strip():
        try:
            parsed_last_cal = date.fromisoformat(last_cal_date.strip())
        except ValueError:
            pass

    parsed_due: date | None = None
    if due_date.strip():
        try:
            parsed_due = date.fromisoformat(due_date.strip())
        except ValueError:
            pass

    eq.name = name.strip()
    eq.serial_number = clean_sn
    eq.scope = scope
    eq.last_cal_date = parsed_last_cal
    eq.due_date = parsed_due
    eq.traceability_body = traceability_body.strip() if traceability_body.strip() else None
    eq.status = equipment_status

    db.commit()
    sync_and_evaluate_equipment_status(db)

    return RedirectResponse(
        url="/equipments?success=Master+equipment+updated+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/equipments/{id}/delete")
def action_equipments_delete(
    id: int, db: Session = Depends(get_db)
) -> RedirectResponse:
    """Delete master equipment with ISO 17025 guardrail preventing deletion if linked to job items."""
    eq = db.get(MasterEquipment, id)
    if not eq:
        return RedirectResponse(
            url="/equipments?error=Master+equipment+not+found",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    linked_count = (
        db.query(JobItem).filter(JobItem.master_equipment_id == id).count()
    )
    if linked_count > 0:
        return RedirectResponse(
            url=(
                f"/equipments?error=Cannot+delete+'{eq.name}':+linked+to+{linked_count}+"
                "calibration+job+item(s)+for+traceability+integrity."
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(eq)
    db.commit()
    return RedirectResponse(
        url="/equipments?success=Master+equipment+deleted+successfully",
        status_code=status.HTTP_303_SEE_OTHER,
    )
