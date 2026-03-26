"""Event task toggle endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.models.event import EventTask
from app.services.auth import require_user
from db import get_db

router = APIRouter()


@router.post("/events/task/toggle")
async def toggle_event_task(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_user),
):
    """Toggle or set/clear a named task for an event.

    Accepts JSON or form data. Parameters accepted:
      - event_id
      - key or task_key
      - action (optional): 'set'|'clear'. If omitted, the endpoint toggles the current state.
    Returns { ok: True, done: <bool> } where done indicates whether task is present (done).
    """
    # Accept either JSON or form-encoded body
    event_id = None
    key = None
    action = None
    try:
        if request.headers.get("content-type", "").lower().startswith("application/json"):
            data = await request.json()
            event_id = data.get("event_id") or data.get("event")
            key = data.get("key") or data.get("task_key")
            action = data.get("action")
        else:
            form = await request.form()
            event_id = form.get("event_id") or form.get("event")
            key = form.get("task_key") or form.get("key")
            action = form.get("action")
    except Exception:
        # fallback: try json then form
        try:
            data = await request.json()
            event_id = data.get("event_id") or data.get("event")
            key = data.get("key") or data.get("task_key")
            action = data.get("action")
        except (ValueError, KeyError):
            try:
                form = await request.form()
                event_id = form.get("event_id") or form.get("event")
                key = form.get("task_key") or form.get("key")
                action = form.get("action")
            except (ValueError, KeyError):
                pass

    if not event_id or not key:
        raise HTTPException(status_code=400, detail="Missing parameters")

    try:
        # Safely coerce user id and event id into ints; return 400 on invalid input
        try:
            uid = int(getattr(user, "UserID", 0))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user id")
        try:
            # Some clients may send event_id as an UploadFile or other types; coerce via str()
            eid = int(str(event_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event_id")

        et = (
            db.query(EventTask)
            .filter(EventTask.EventID == eid, EventTask.UserID == uid, EventTask.Key == key)
            .first()
        )

        # If explicit action requested
        if action in ("set", "clear"):
            if action == "set":
                if not et:
                    et = EventTask(
                        EventID=eid,
                        UserID=uid,
                        Key=key,
                        State="done",
                        CompletedAt=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    db.add(et)
                else:
                    setattr(et, "State", "done")
                    setattr(et, "CompletedAt", datetime.now(timezone.utc).replace(tzinfo=None))
                db.commit()
                return {"ok": True, "done": True}
            else:
                if et:
                    db.delete(et)
                    db.commit()
                return {"ok": True, "done": False}

        # Toggle: if exists remove it (pending), otherwise create it (done)
        if et:
            db.delete(et)
            db.commit()
            return {"ok": True, "done": False}
        else:
            new_et = EventTask(
                EventID=eid,
                UserID=uid,
                Key=key,
                State="done",
                CompletedAt=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(new_et)
            db.commit()
            return {"ok": True, "done": True}
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
