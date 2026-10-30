from __future__ import annotations

from app.models.job_item import JobItem, JobStatus
from app.models.order import Order, POStatus


def sync_job_item_release(item: JobItem, po_status: POStatus) -> bool:
    """Enforce Admin Hold Logic on a single JobItem.

    Rules:
    - If po_status == RECEIVED:
      - Automatically sets release_allowed = True
      - Moves any item in HOLD_ADMIN to CERT_READY
    - If po_status == PENDING:
      - Sets release_allowed = False
      - Moves any item in CERT_READY to HOLD_ADMIN
    """
    if po_status == POStatus.RECEIVED:
        if item.status == JobStatus.HOLD_ADMIN:
            item.status = JobStatus.CERT_READY
        item.release_allowed = True
    else:
        if item.status == JobStatus.CERT_READY:
            item.status = JobStatus.HOLD_ADMIN
        item.release_allowed = False
    return item.release_allowed


def sync_order_job_items_release(order: Order) -> None:
    """Enforce Admin Hold Logic across all JobItems belonging to an Order."""
    for item in order.job_items:
        sync_job_item_release(item, order.po_status)
