from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import (
    alerts_router,
    bast_router,
    customers_router,
    dashboard_router,
    equipments_router,
    job_items_router,
    kanban_router,
    orders_router,
    po_out_router,
    subcontractors_router,
)
from app.services.storage import init_storage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_storage()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Calibration Lab Tracking System", lifespan=lifespan)

# --- Register Routers ---
app.include_router(dashboard_router)
app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(bast_router)
app.include_router(kanban_router)
app.include_router(job_items_router)
app.include_router(equipments_router)
app.include_router(alerts_router)
app.include_router(subcontractors_router)
app.include_router(po_out_router)

# --- Static Files & Favicon ---
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.ico")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
