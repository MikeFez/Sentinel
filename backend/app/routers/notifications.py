from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Notification
from ..services import notifier

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def get_notifications(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    """Where notifications go (service names only, never the URLs) and the latest ones sent."""
    rows = db.query(Notification).order_by(Notification.at.desc()).limit(limit)
    return {
        "services": notifier.services(),
        "recent": [
            {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "status": n.status, "error": n.error,
             "at": n.at, "company_id": n.company_id}
            for n in rows
        ],
    }


@router.post("/test")
def send_test(db: Session = Depends(get_db)):
    """Send a test notification to every destination, ignoring the on/off switches."""
    if not notifier.destinations():  # nothing to try: don't record a failed send
        return {"ok": False, "error": "No destinations: set the NOTIFY_URLS environment variable"}
    row = notifier.notify(db, "test", "test", "Sentinel test notification",
                          "Notifications are working. You'll get alerts, sentiment changes and news here.", force=True)
    if row is None:
        return {"ok": False, "error": "Could not send (see the container log)"}
    return {"ok": row.status == "sent", "error": row.error}
