"""
Make sure Celery app is always imported when Django starts
so that shared_task uses this app.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
