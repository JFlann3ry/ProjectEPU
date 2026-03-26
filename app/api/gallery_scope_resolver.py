from sqlalchemy.orm import Session

from app.api.gallery_scope_shared import GALLERY_COOKIE, _verify_scope
from app.models.event import Event


def get_scoped_event_id(request, db: Session, user_id: int) -> int | None:
    """Resolve selected gallery event id from signed cookie within user ownership scope."""
    selected_event_id: int | None = None
    scope_cookie = request.cookies.get(GALLERY_COOKIE)
    if scope_cookie:
        raw = _verify_scope(scope_cookie) or None
        if raw:
            try:
                eid = int(raw)
            except Exception:
                eid = None
            if eid is not None:
                owned = (
                    db.query(Event.EventID)
                    .filter(Event.EventID == eid, Event.UserID == user_id)
                    .first()
                )
                if owned:
                    selected_event_id = eid
    return selected_event_id
