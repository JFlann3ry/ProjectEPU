"""Background job scheduler and job definitions."""

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings
from app.jobs.maintenance import purge_soft_deleted_files

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler | None:
    """Get the global background scheduler instance."""
    return _scheduler


def init_scheduler():
    """Initialize the background scheduler with job definitions."""
    global _scheduler
    if _scheduler is not None:
        return  # Already initialized

    _scheduler = BackgroundScheduler()

    # Create a database engine for background jobs
    # (use the same connection settings as the app)
    try:
        db_url = str(settings.DATABASE_URL)
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def job_purge_soft_deleted():
            """Purge soft-deleted files (wrapped for scheduler)."""
            db = SessionLocal()
            try:
                result = purge_soft_deleted_files(db, retention_days=30, batch_size=1_000)
                print(f"[SCHEDULER] Soft-deleted file purge completed: {result}")
            except Exception as e:
                print(f"[SCHEDULER] Soft-deleted file purge failed: {e}")
            finally:
                db.close()

        # Schedule purge job to run daily at 2 AM (UTC)
        _scheduler.add_job(
            job_purge_soft_deleted,
            trigger=CronTrigger(hour=2, minute=0, second=0),
            id="purge_soft_deleted_files_daily",
            name="Purge soft-deleted files (daily)",
            replace_existing=True,
        )

        _scheduler.start()
        print("[SCHEDULER] Background scheduler started successfully")
    except Exception as e:
        print(f"[SCHEDULER] Failed to initialize background scheduler: {e}")
        _scheduler = None


def shutdown_scheduler():
    """Shutdown the background scheduler."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        print("[SCHEDULER] Background scheduler shutdown")
        _scheduler = None


@asynccontextmanager
async def lifespan(app):
    """FastAPI lifespan context manager for scheduler startup/shutdown.

    Usage in main.py:
        app = FastAPI(lifespan=lifespan)
    """
    # Startup
    init_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
