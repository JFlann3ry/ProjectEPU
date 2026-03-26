from fastapi import APIRouter

from app.api.events_assets import router as events_assets_router
from app.api.events_collections import router as events_collections_router
from app.api.events_dashboard import router as events_dashboard_router
from app.api.events_details import router as events_details_router
from app.api.events_editing import router as events_editing_router
from app.api.events_tasks import router as events_tasks_router
from app.api.events_uploads import router as events_uploads_router

router = APIRouter()

# Event management routers (editing, dashboard, asset management, collections)
router.include_router(events_editing_router)
router.include_router(events_collections_router)
router.include_router(events_details_router)
router.include_router(events_assets_router)
router.include_router(events_dashboard_router)

# Event file/task management routers
router.include_router(events_uploads_router)
router.include_router(events_tasks_router)
