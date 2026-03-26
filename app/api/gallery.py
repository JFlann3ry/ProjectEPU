# ruff: noqa: I001
from fastapi import APIRouter

from app.api import gallery_builders
from app.api import gallery_mutations
from app.api.gallery_actions import router as gallery_actions_router
from app.api.gallery_data import router as gallery_data_router
from app.api.gallery_downloads import router as gallery_downloads_router
from app.api.gallery_mutations import router as gallery_mutations_router
from app.api.gallery_order import router as gallery_order_router
from app.api.gallery_pages import router as gallery_pages_router
from app.api.gallery_scope import router as gallery_scope_router
from app.api.gallery_view import router as gallery_view_router

router = APIRouter()

# Backward compatibility for modules importing DELETION_LOGS from app.api.gallery.
DELETION_LOGS = gallery_mutations.DELETION_LOGS
_build_gallery_files = gallery_builders._build_gallery_files
_build_gallery_ids = gallery_builders._build_gallery_ids
_has_deleted_at = gallery_builders._has_deleted_at

router.include_router(gallery_pages_router)
router.include_router(gallery_mutations_router)
router.include_router(gallery_downloads_router)
router.include_router(gallery_scope_router)
router.include_router(gallery_data_router)
router.include_router(gallery_order_router)
router.include_router(gallery_view_router)
router.include_router(gallery_actions_router)
