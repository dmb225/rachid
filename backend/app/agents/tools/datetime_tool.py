"""Date and time utilities for agents."""

from datetime import datetime


def get_current_datetime() -> str:
    """Get the current date and time.

    Returns:
        A string with the current date and time.
    """
    now = datetime.now()
    return f"Current date: {now.strftime('%Y-%m-%d')}, Current time: {now.strftime('%H:%M:%S')}"
