"""
Shared pytest fixtures and configuration.
"""

import pytest


@pytest.fixture(autouse=True)
def celery_eager_mode(settings):
    """Run Celery tasks synchronously during tests."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
