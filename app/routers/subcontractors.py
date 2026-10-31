from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_item import JobItem
from app.models.subcontractor import Subcontractor
from app.schemas.subcontractor import (
    SubcontractorCreate,
    SubcontractorRead,
    SubcontractorUpdate,
)
from app.templates_config import templates

router = APIRouter()


# ==========================================
# REST API ENDPOINTS
# ==========================================


@router.get("/api/subcontractors", response_model=list[SubcontractorRead])
def api_list_subcontractors(
    db: Session = Depends(get_db),
) -> list[Subcontractor]:
    return db.query(Subcontractor).order_by(Subcontractor.vendor_name).all()


@router.post(
    "/api/subcontractors",
    response_model=SubcontractorRead,
    status_code=status.HTTP_201_CREATED,
)
def api_create_subcontractor(
    payload: SubcontractorCreate, db: Session = Depends(get_db)
) -> Subcontractor:
    sub = Subcontractor(
        vendor_name=payload.vendor_name.strip(),
        pic_name=payload.pic_name.strip() if payload.pic_name else None,
        phone=payload.phone.strip() if payload.phone else None,
        email=payload.email.strip() if payload.email else None,
        address=payload.address.strip() if payload.address else None,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/api/subcontractors/{id}", response_model=SubcontractorRead)
def api_get_subcontractor(id: int, db: Session = Depends(get_db)) -> Subcontractor:
    sub = db.get(Subcontractor, id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subcontractor not found"
        )
    return sub


@router.put("/api/subcontractors/{id}", response_model=SubcontractorRead)
def api_update_subcontractor(
    id: int, payload: SubcontractorUpdate, db: Session = Depends(get_db)
) -> Subcontractor:
    sub = db.get(Subcontractor, id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subcontractor not found"
        )

    if payload.vendor_name is not None:
        sub.vendor_name = payload.vendor_name.strip()
    if payload.pic_name is not None:
        sub.pic_name = payload.pic_name.strip() if payload.pic_name else None
    if payload.phone is not None:
        sub.phone = payload.phone.strip() if payload.phone else None
    if payload.email is not None:
        sub.email = payload.email.strip() if payload.email else None
    if payload.address is not None:
        sub.address = payload.address.strip() if payload.address else None

    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/api/subcontractors/{id}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_subcontractor(id: int, db: Session = Depends(get_db)) -> None:
    sub = db.get(Subcontractor, id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subcontractor not found"
        )
    linked = db.query(JobItem).filter(JobItem.subcontractor_id == id).count()
    if linked > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete subcontractor '{sub.vendor_name}': linked to {linked} job items.",
        )
    db.delete(sub)
    db.commit()


# ==========================================
# HTML WEB VIEWS
# ==========================================


@router.get("/subcontractors", response_class=HTMLResponse)
def page_subcontractors_index(
    request: Request,
    q: str | None = None,
    error: str | None = None,
    success: str | None = None,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    query = db.query(Subcontractor)
    if q:
        pat = f"%{q.strip()}%"
        query = query.filter(
            (Subcontractor.vendor_name.ilike(pat))
            | (Subcontractor.pic_name.ilike(pat))
            | (Subcontractor.email.ilike(pat))
            | (Subcontractor.phone.ilike(pat))
        )
    subs = query.order_by(Subcontractor.vendor_name).all()

    return templates.TemplateResponse(
        request=request,
        name="subcontractors/index.html",
        context={
            "subcontractors": subs,
            "total_count": len(subs),
            "search_query": q or "",
            "error_msg": error,
            "success_msg": success,
        },
    )


@router.get("/subcontractors/create", response_class=HTMLResponse)
def page_subcontractors_create(
    request: Request, error: str | None = None
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="subcontractors/form.html",
        context={"is_edit": False, "sub": None, "error_msg": error},
    )


@router.post("/subcontractors", response_model=None)
def action_subcontractors_create(
    request: Request,
    vendor_name: str = Form(...),
    pic_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    db: Session = Depends(get_db),
) -> Response:
    sub = Subcontractor(
        vendor_name=vendor_name.strip(),
        pic_name=pic_name.strip() if pic_name.strip() else None,
        phone=phone.strip() if phone.strip() else None,
        email=email.strip() if email.strip() else None,
        address=address.strip() if address.strip() else None,
    )
    db.add(sub)
    db.commit()
    return RedirectResponse(
        url="/subcontractors?success=Subcontractor+berhasil+didaftarkan",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/subcontractors/{id}/edit", response_class=HTMLResponse)
def page_subcontractors_edit(
    id: int, request: Request, error: str | None = None, db: Session = Depends(get_db)
) -> HTMLResponse:
    sub = db.get(Subcontractor, id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subcontractor not found"
        )
    return templates.TemplateResponse(
        request=request,
        name="subcontractors/form.html",
        context={"is_edit": True, "sub": sub, "error_msg": error},
    )


@router.post("/subcontractors/{id}/edit", response_model=None)
def action_subcontractors_edit(
    id: int,
    request: Request,
    vendor_name: str = Form(...),
    pic_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    db: Session = Depends(get_db),
) -> Response:
    sub = db.get(Subcontractor, id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subcontractor not found"
        )

    sub.vendor_name = vendor_name.strip()
    sub.pic_name = pic_name.strip() if pic_name.strip() else None
    sub.phone = phone.strip() if phone.strip() else None
    sub.email = email.strip() if email.strip() else None
    sub.address = address.strip() if address.strip() else None

    db.commit()
    return RedirectResponse(
        url="/subcontractors?success=Data+subcontractor+berhasil+diperbarui",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/subcontractors/{id}/delete")
def action_subcontractors_delete(
    id: int, db: Session = Depends(get_db)
) -> RedirectResponse:
    sub = db.get(Subcontractor, id)
    if not sub:
        return RedirectResponse(
            url="/subcontractors?error=Subcontractor+tidak+ditemukan",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    linked = db.query(JobItem).filter(JobItem.subcontractor_id == id).count()
    if linked > 0:
        return RedirectResponse(
            url=(
                f"/subcontractors?error=Gagal+hapus:+Vendor+{sub.vendor_name}+"
                f"masih+terkait+dengan+{linked}+instrumen+kalibrasi."
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    db.delete(sub)
    db.commit()
    return RedirectResponse(
        url="/subcontractors?success=Subcontractor+berhasil+dihapus",
        status_code=status.HTTP_303_SEE_OTHER,
    )
