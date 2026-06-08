"""
SEPEHR Backend — Maintenance Celery Tasks
"""

import logging
from datetime import datetime, timedelta, timezone

from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.maintenance.cleanup_expired_tokens")
def cleanup_expired_tokens() -> dict:
    """Remove expired refresh tokens from the database."""
    import asyncio
    from sqlalchemy import delete
    from app.infrastructure.database.session import AsyncSessionFactory
    from app.domain.models.all import RefreshToken

    async def _cleanup():
        async with AsyncSessionFactory() as db:
            cutoff = datetime.now(timezone.utc)
            result = await db.execute(
                delete(RefreshToken).where(RefreshToken.expires_at < cutoff)
            )
            await db.commit()
            return result.rowcount

    count = asyncio.run(_cleanup())
    logger.info(f"Cleaned up {count} expired refresh tokens")
    return {"deleted": count}


@celery_app.task(name="app.tasks.maintenance.cleanup_orphaned_files")
def cleanup_orphaned_files() -> dict:
    """Remove MinIO files not referenced by any message."""
    # Implementation would scan MinIO objects and compare against DB
    logger.info("Orphaned file cleanup task started")
    return {"status": "ok"}
