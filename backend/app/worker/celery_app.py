import os

from celery import Celery

from app.logging_config import setup_logging

setup_logging()

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery = Celery("bitwise", broker=redis_url, backend=redis_url)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,  # 10 minutes soft limit
    task_time_limit=660,  # 11 minutes hard kill
)

celery.autodiscover_tasks(["app.worker"])
