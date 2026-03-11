#!/usr/bin/env bash

# Start Gunicorn in the foreground
# Note: Celery worker is omitted here because we set CELERY_TASK_ALWAYS_EAGER=True 
# in render.yaml to run tasks synchronously (since Render doesn't have a free Redis tier)
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3
