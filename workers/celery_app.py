"""
Celery application configuration for async task processing.
"""

from celery import Celery

from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "football_kb_workers",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

if __name__ == "__main__":
    celery_app.start()
