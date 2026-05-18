"""
Celery application.

To start the worker (from backend/):
    celery -A app.tasks worker --loglevel=info --concurrency=2
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "portai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.portfolio"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Retry failed tasks up to 2 times with 30s backoff
    task_default_retry_delay=30,
    task_max_retries=2,
)
