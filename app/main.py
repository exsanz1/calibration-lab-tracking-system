from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import (
    bast_router,
    customers_router,
    dashboard_router,
    orders_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Calibration Lab Tracking System", lifespan=lifespan)

# --- Register Routers ---
app.include_router(dashboard_router)
app.include_router(customers_router)
app.include_router(orders_router)
app.include_router(bast_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
