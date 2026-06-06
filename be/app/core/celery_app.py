from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "blood_warriors",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.optimization_tasks",
        "app.tasks.orchestration_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Configure periodic tasks for checking timeouts
    beat_schedule={
        "process-timeouts-every-minute": {
            "task": "app.tasks.orchestration_tasks.process_match_timeouts",
            "schedule": 60.0, # Every 60 seconds (for testing, tune for prod)
        }
    }
)
