from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.job_item import JobItem, JobStatus, Scope
from app.models.master_equipment import EquipmentStatus, MasterEquipment
from app.models.order import Order
from app.schemas.job_item import JobItemRead
from app.schemas.master_equipment import MasterEquipmentRead
from app.services.admin_hold import sync_job_item_release
from app.services.storage import save_certificate, save_worksheet
from app.services.traceability import validate_master_equipment
from app.templates_config import templates

router = APIRouter()


# --- API Helper Endpoints ---

@router.get("/api/master-equipments/active", response_model=list[MasterEquipmentRead])
def api_get_active_master_equipments(
    scope: Scope | None = None, db: Session = Depends(get_db)
) -> list[MasterEquipment]:
    """Return all ACTIVE master equipment, optionally filtered by scope."""
    query = db.query(MasterEquipment).filter(
        MasterEquipment.status == EquipmentStatus.ACTIVE
    )
    if scope:
        query = query.filter(MasterEquipment.scope == scope)
    return query.order_by(MasterEquipment.name).all()


# --- HTML & Action Endpoints for Job Items ---

@router.get("/job-items/{item_id}", response_class=HTMLResponse)
def page_job_item_detail(
    item_id: int, request: Request, db: Session = Depends(get_db)
) -> HTMLResponse:
    item = (
        db.query(JobItem)
        .options(
            joinedload(JobItem.order).joinedload(Order.customer),
            joinedload(JobItem.master_equipment),
        )
        .filter(JobItem.id == item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

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
        name="kanban/modal_detail.html",
        context={
            "item": item,
            "order": item.order,
            "active_masters": active_masters,
            "statuses": all_statuses,
        },
    )


@router.post("/job-items/{item_id}/status")
def update_item_status(
    item_id: int,
    db: Session = Depends(get_db),
    status: str = Form(...),
    assigned_tech: str = Form(""),
    redirect_url: str = Form("/kanban"),
) -> RedirectResponse:
    item = db.query(JobItem).options(joinedload(JobItem.order)).filter(JobItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    target_status = JobStatus(status)

    # CRITICAL GUARDRAIL: Block transition to DELIVERED if release_allowed == False
    if target_status == JobStatus.DELIVERED and not item.release_allowed:
        raise HTTPException(
            status_code=403,
            detail=(
                "Status transition blocked: Cannot mark instrument as DELIVERED because "
                "certificate release is restricted by Admin Hold (Customer PO is PENDING)."
            ),
        )

    item.status = target_status
    if assigned_tech:
        item.assigned_tech = assigned_tech

    # Apply Admin Hold logic if status changed to CERT_READY
    sync_job_item_release(item, item.order.po_status)

    db.commit()
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/job-items/{item_id}/link-master")
def link_master_equipment(
    item_id: int,
    db: Session = Depends(get_db),
    master_equipment_id: int = Form(...),
    redirect_url: str = Form("/kanban"),
) -> RedirectResponse:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    # Guardrail check: active status and matching scope
    validate_master_equipment(db, master_equipment_id, item.scope)

    item.master_equipment_id = master_equipment_id
    db.commit()
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/job-items/{item_id}/upload-worksheet")
def upload_worksheet_file(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    redirect_url: str = Form("/kanban"),
) -> RedirectResponse:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    saved_path = save_worksheet(item.qr_tag, file)
    item.worksheet_file_path = saved_path
    db.commit()
    return RedirectResponse(url=redirect_url, status_code=303)


@router.post("/job-items/{item_id}/upload-certificate")
def upload_certificate_file(
    item_id: int,
    file: UploadFile = File(...),
    certificate_no: str = Form(""),
    db: Session = Depends(get_db),
    redirect_url: str = Form("/kanban"),
) -> RedirectResponse:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    saved_path = save_certificate(item.qr_tag, file)
    item.certificate_file_path = saved_path
    if certificate_no:
        item.certificate_no = certificate_no

    db.commit()
    return RedirectResponse(url=redirect_url, status_code=303)


# --- Protected File Downloads ---

@router.get("/job-items/{item_id}/certificate")
def download_certificate(
    item_id: int, db: Session = Depends(get_db)
) -> FileResponse:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    # CRITICAL ISO/IEC 17025 GUARDRAIL: Protected download endpoint
    if not item.release_allowed:
        raise HTTPException(
            status_code=403,
            detail=(
                "Access Forbidden: Certificate download is blocked by Admin Hold. "
                "Customer PO is PENDING. Commercial release approval required."
            ),
        )

    if not item.certificate_file_path:
        raise HTTPException(
            status_code=404,
            detail="No certificate file has been uploaded for this instrument.",
        )

    file_path = Path(item.certificate_file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Certificate file not found on disk.")

    download_filename = f"Certificate_{item.certificate_no or item.qr_tag}.pdf"
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=download_filename,
    )


@router.get("/job-items/{item_id}/worksheet")
def download_worksheet(item_id: int, db: Session = Depends(get_db)) -> FileResponse:
    item = db.get(JobItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Job item not found")

    if not item.worksheet_file_path:
        raise HTTPException(
            status_code=404,
            detail="No worksheet file has been uploaded for this instrument.",
        )

    file_path = Path(item.worksheet_file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Worksheet file not found on disk.")

    return FileResponse(
        path=file_path,
        filename=f"Worksheet_{item.qr_tag}{file_path.suffix}",
    )
