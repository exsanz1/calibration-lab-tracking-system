from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.alert import DailyAlertSummary
from app.services.alerts import generate_daily_alerts

router = APIRouter()


@router.get("/api/alerts/daily", response_model=DailyAlertSummary)
def api_daily_alerts(db: Session = Depends(get_db)) -> DailyAlertSummary:
    """Daily summary alert endpoint for automated reporting and webhooks (WhatsApp/Telegram).

    Returns:
    1. sla_alerts: Non-delivered job items approaching target SLA date (<= 3 days) or overdue.
    2. admin_holds: Items at CERT_READY stage blocked by PO Pending (release_allowed == False).
    3. master_alerts: Master equipments expiring within 60 days, 30 days, or already EXPIRED.
    """
    return generate_daily_alerts(db)
