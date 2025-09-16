from sqlalchemy.orm import Session

from app.services.photo_order_service import rebuild_event_gallery_order


def run_rebuild_for_event(db: Session, event_id: int) -> int:
    """Run the rebuild job for a single event and return number of rows created."""
    created = rebuild_event_gallery_order(db, event_id)
    # rebuild_event_gallery_order returns a list of inserted row dicts
    return len(created)
