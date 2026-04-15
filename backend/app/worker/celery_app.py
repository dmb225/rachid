"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "rachid",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

# Autodiscover tasks from app.worker.tasks module
celery_app.autodiscover_tasks(["app.worker.tasks"])


celery_app.conf.beat_schedule = {
    "example-every-minute": {
        "task": "app.worker.tasks.examples.example_task",
        "schedule": 60.0,  # Every 60 seconds
        "args": ("periodic",),
    },
    # Example with crontab (runs at 00:00 every day)
    # "daily-cleanup": {
    #     "task": "app.worker.tasks.examples.cleanup_task",
    #     "schedule": crontab(hour=0, minute=0),
    # },
}
celery_app.conf.beat_schedule["rag-sync-check"] = {
    "task": "app.worker.tasks.rag_tasks.check_scheduled_syncs",
    "schedule": 60.0,  # Every 60 seconds
}
