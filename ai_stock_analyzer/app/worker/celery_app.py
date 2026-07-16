"""
AI Stock Analyzer - Celery Application (Sprint 4 Stub)
Akan dikonfigurasi penuh pada Sprint 4.
"""
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "ai_stock_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    beat_schedule={
        "daily-eod-analysis-1730": {
            "task": "task_daily_batch_analysis",
            "schedule": crontab(hour=17, minute=30),
            "options": {"queue": "default"}
        },
    }
)
