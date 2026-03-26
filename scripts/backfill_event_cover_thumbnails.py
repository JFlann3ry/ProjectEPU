"""
Backfill dashboard cover thumbnails for event banners.

Usage (from project root):
    venv\\Scripts\\python.exe scripts/backfill_event_cover_thumbnails.py
    venv\\Scripts\\python.exe scripts/backfill_event_cover_thumbnails.py --event 123
    venv\\Scripts\\python.exe scripts/backfill_event_cover_thumbnails.py --user 45 --force
"""

import argparse

from sqlalchemy.orm import Session

from app.models.event import Event, EventCustomisation
from app.services.thumbs import ensure_dashboard_cover_thumbnail
from db import get_db


def process(
    db: Session,
    user_id: int | None,
    event_id: int | None,
    width: int,
    force: bool,
) -> dict[str, int]:
    stats = {
        "scanned": 0,
        "eligible": 0,
        "generated": 0,
        "failed": 0,
        "skipped": 0,
    }

    q = db.query(EventCustomisation, Event).join(Event, Event.EventID == EventCustomisation.EventID)
    if user_id is not None:
        q = q.filter(Event.UserID == int(user_id))
    if event_id is not None:
        q = q.filter(Event.EventID == int(event_id))

    rows = q.all()
    for custom, _event in rows:
        stats["scanned"] += 1
        cover_path = str(getattr(custom, "CoverPhotoPath", "") or "")
        if not cover_path.startswith("/static/uploads/"):
            stats["skipped"] += 1
            continue
        stats["eligible"] += 1
        thumb_url = ensure_dashboard_cover_thumbnail(
            cover_path,
            width=int(width),
            force=bool(force),
        )
        if thumb_url:
            stats["generated"] += 1
        else:
            stats["failed"] += 1

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill dashboard cover thumbnails for event banners",
    )
    parser.add_argument("--event", type=int, default=None, help="Limit to EventID")
    parser.add_argument("--user", type=int, default=None, help="Limit to UserID")
    parser.add_argument("--width", type=int, default=480, help="Thumbnail width")
    parser.add_argument("--force", action="store_true", help="Regenerate existing thumbs")
    args = parser.parse_args()

    db_gen = get_db()
    db = next(db_gen)
    try:
        stats = process(
            db,
            user_id=args.user,
            event_id=args.event,
            width=int(args.width),
            force=bool(args.force),
        )
        print(
            "scanned={scanned} eligible={eligible} generated={generated} "
            "failed={failed} skipped={skipped}".format(**stats)
        )
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    main()
