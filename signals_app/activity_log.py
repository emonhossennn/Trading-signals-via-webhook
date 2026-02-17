"""
Activity logging helper.

Provides a simple function to record user actions and system events
in the ActivityLog table for auditing and debugging.
"""

import logging

from .models import ActivityLog

logger = logging.getLogger(__name__)


def log_activity(user, action: str, details: dict = None):
    """
    Create an activity log entry.

    Args:
        user: Django User instance (or None for system events).
        action: Short description, e.g. 'signal_received', 'order_created'.
        details: Optional dict with additional context.
    """
    entry = ActivityLog.objects.create(
        user=user,
        action=action,
        details=details or {},
    )
    logger.info(f"Activity logged: [{action}] user={user} details={details}")
    return entry
