from fastapi import APIRouter

from app.api.events_edit_submit_code import router as events_edit_submit_code_router
from app.api.events_edit_submit_numeric import (
    edit_event_submit,
)
from app.api.events_edit_submit_numeric import (
    router as events_edit_submit_numeric_router,
)

router = APIRouter()
router.include_router(events_edit_submit_numeric_router)
router.include_router(events_edit_submit_code_router)

__all__ = ["router", "edit_event_submit"]
