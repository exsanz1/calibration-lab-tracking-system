from __future__ import annotations

from app.routers.alerts import router as alerts_router
from app.routers.bast import router as bast_router
from app.routers.customers import router as customers_router
from app.routers.dashboard import router as dashboard_router
from app.routers.equipments import router as equipments_router
from app.routers.job_items import router as job_items_router
from app.routers.kanban import router as kanban_router
from app.routers.orders import router as orders_router

__all__ = [
    "dashboard_router",
    "customers_router",
    "orders_router",
    "bast_router",
    "kanban_router",
    "job_items_router",
    "equipments_router",
    "alerts_router",
]
