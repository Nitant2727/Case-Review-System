"""
Celery tasks for async notifications.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification(self, event: str, case_id: str, recipient_id: str, details: dict):
    """
    Async notification trigger.

    In production this would integrate with email / Slack / push notification
    services. For now we log the notification.
    """
    try:
        logger.info(
            "NOTIFICATION [%s] case=%s recipient=%s details=%s",
            event,
            case_id,
            recipient_id,
            details,
        )
        # Placeholder: integrate with actual notification backend here
        # e.g. send_email(recipient_id, ...) or push to webhook
        return {
            "status": "sent",
            "event": event,
            "case_id": case_id,
            "recipient_id": recipient_id,
        }
    except Exception as exc:
        logger.error("Failed to send notification: %s", exc)
        raise self.retry(exc=exc)
