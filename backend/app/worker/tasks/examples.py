"""Example Celery tasks."""

import logging
import time
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)  # type: ignore
def example_task(self: Any, message: str) -> dict[str, Any]:
    """
    Example task that processes a message.

    Args:
        message: Message to process

    Returns:
        Result dictionary with processed message
    """
    logger.info(f"Processing message: {message}")

    try:
        # Simulate some work
        time.sleep(1)

        result = {
            "status": "completed",
            "message": f"Processed: {message}",
            "task_id": self.request.id,
        }
        logger.info(f"Task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc


@shared_task(bind=True)  # type: ignore
def long_running_task(self: Any, duration: int = 10) -> dict[str, Any]:
    """
    Example long-running task with progress updates.

    Args:
        duration: Duration in seconds

    Returns:
        Result dictionary
    """
    logger.info(f"Starting long-running task for {duration} seconds")

    for i in range(duration):
        time.sleep(1)
        # Update task state with progress
        self.update_state(state="PROGRESS", meta={"current": i + 1, "total": duration})
        logger.info(f"Progress: {i + 1}/{duration}")

    return {
        "status": "completed",
        "duration": duration,
        "task_id": self.request.id,
    }


@shared_task  # type: ignore
def send_email_task(to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Example email sending task.

    Replace with actual email sending logic (e.g., using smtp, sendgrid, etc.)

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Result dictionary
    """
    logger.info(f"Sending email to {to}: {subject}")

    # TODO: Implement actual email sending
    # Example with SMTP:
    # import smtplib
    # from email.mime.text import MIMEText
    # ...

    # Simulate sending
    time.sleep(0.5)

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
    }
