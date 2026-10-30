from __future__ import annotations

from app.models.job_item import JobItem, JobStatus
from app.models.order import Order, POStatus


def sync_job_item_release(item: JobItem, po_status: POStatus) -> bool:
    """Enforce Admin Hold Logic on a single JobItem.

    Rules:
    - If po_status == PENDING: release_allowed = False (certificates are blocked,
      even if technical status reaches CERT_READY).
    - If po_status == RECEIVED and status == CERT_READY: release_allowed = True.
    - Any other status: release_allowed = False.
    """
    if po_status == POStatus.RECEIVED and item.status == JobStatus.CERT_READY:
        item.release_allowed = True
    else:
        item.release_allowed = False
    return item.release_allowed


def sync_order_job_items_release(order: Order) -> None:
    """Enforce Admin Hold Logic across all JobItems belonging to an Order."""
    for item in order.job_items:
        sync_job_item_release(item, order.po_status)
