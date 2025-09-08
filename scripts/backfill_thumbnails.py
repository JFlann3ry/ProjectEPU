"""
Backfill thumbnails/posters for existing uploads.

Usage (from project root):
    venv\\Scripts\\python.exe -m scripts.backfill_thumbnails [--event EVENT_ID] [--user USER_ID]

Without flags it processes all events/files. Requires local storage mounted at storage/.
"""
import argparse
import os

from sqlalchemy.orm import Session

from app.models.event import Event, FileMetadata
from app.services.thumbs import generate_all_thumbs_for_file
from db import get_db


def process(db: Session, user_id: int | None, event_id: int | None) -> int:
    q = db.query(FileMetadata).join(Event, Event.EventID == FileMetadata.EventID)
    if user_id is not None:
        q = q.filter(Event.UserID == int(user_id))
    if event_id is not None:
        q = q.filter(Event.EventID == int(event_id))
    files = q.all()
    count = 0
    for f in files:
        uid = int(getattr(db.query(Event).filter(Event.EventID == f.EventID).first(), 'UserID'))
        eid = int(getattr(f, 'EventID'))
        fid = int(getattr(f, 'FileMetadataID'))
        ftype = str(getattr(f, 'FileType'))
        fname = str(getattr(f, 'FileName'))
        base = os.path.join('storage', str(uid), str(eid), fname)
        if not os.path.exists(base):
            continue
        generate_all_thumbs_for_file(uid, eid, fid, ftype, fname)
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description='Backfill thumbnails for existing uploads')
    parser.add_argument('--event', type=int, default=None, help='EventID to limit')
    parser.add_argument('--user', type=int, default=None, help='UserID to limit')
    args = parser.parse_args()

    db_gen = get_db()
    db = next(db_gen)
    try:
        num = process(db, args.user, args.event)
        print(f"Processed {num} files")
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == '__main__':
    main()
