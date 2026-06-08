"""
SEPEHR Backend — Celery Worker Configuration
"""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "sepehr",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.maintenance", "app.tasks.notifications"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tehran",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.tasks.maintenance.cleanup_expired_tokens",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-orphaned-files": {
            "task": "app.tasks.maintenance.cleanup_orphaned_files",
            "schedule": 86400.0,  # Every day
        },
    },
)

app = celery_app
