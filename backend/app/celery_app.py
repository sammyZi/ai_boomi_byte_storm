"""Celery application configuration for asynchronous task execution.

This module configures Celery with Redis as the broker and backend
for managing docking jobs and other async tasks.
"""

from celery import Celery
from config.settings import settings

# Create Celery app
celery_app = Celery(
    "drug_discovery",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.docking.celery_tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_expires=86400 * 7,  # Results expire after 7 days
    
    # Worker settings - use solo pool on Windows to avoid permission issues
    worker_pool="solo",  # Required for Windows compatibility
    worker_concurrency=1,  # Solo pool only supports 1 concurrent task
    
    # Task routing
    task_routes={
        "app.docking.celery_tasks.run_docking_task": {"queue": "docking"},
        "app.docking.celery_tasks.cleanup_old_jobs": {"queue": "maintenance"},
    },
    
    # Rate limiting for docking jobs
    task_annotations={
        "app.docking.celery_tasks.run_docking_task": {
            "rate_limit": f"{settings.docking_max_concurrent}/m"
        }
    },
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=2,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-old-docking-jobs": {
            "task": "app.docking.celery_tasks.cleanup_old_jobs",
            "schedule": 86400,  # Run daily
        }
    }
)


def get_celery_app() -> Celery:
    """Get the configured Celery application instance."""
    return celery_app
