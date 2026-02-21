"""
Order manager — order creation, broker execution, lifecycle simulation.

Uses a plain daemon thread to drive status transitions so we don't need
Celery or any external task queue for this service.
"""

import logging
import threading
import time
from decimal import Decimal

from .models import Order
from .signal_parser import ParsedSignal
from .mock_broker import execute_trade
from .activity_log import log_activity

logger = logging.getLogger(__name__)


def create_and_process_order(user, broker_account, signal: ParsedSignal) -> Order:
    """
    Persist an order, hand it off to the mock broker, then kick off the
    background lifecycle thread.

    The row is written as 'pending' before the broker call so there is
    always an audit trail even when execution fails.
    """
    order = Order.objects.create(
        user=user,
        broker_account=broker_account,
        action=signal.action,
        instrument=signal.instrument,
        entry_price=Decimal(str(signal.entry_price)) if signal.entry_price else None,
        stop_loss=Decimal(str(signal.stop_loss)),
        take_profit=Decimal(str(signal.take_profit)),
        status="pending",
        fake_order_id="",
    )

    log_activity(user, "order_created", {
        "order_id": str(order.id),
        "action": signal.action,
        "instrument": signal.instrument,
    })

    try:
        result = execute_trade(signal, user, broker_account)
        order.fake_order_id = result.order_id
        order.save(update_fields=["fake_order_id", "updated_at"])
        log_activity(user, "order_submitted", {
            "order_id": str(order.id),
            "fake_order_id": result.order_id,
        })
    except Exception as exc:
        logger.error("Broker execution failed for order %s: %s", order.id, exc)
        return order

    thread = threading.Thread(
        target=_simulate_order_lifecycle,
        args=(str(order.id), user.id),
        daemon=True,
    )
    thread.start()

    return order


def _simulate_order_lifecycle(order_id: str, user_id: int):
    """
    Background thread: pending -> executed (after 5 s) -> closed (after 10 s).
    Each transition is broadcast to the user's WebSocket group.
    """
    from .models import Order
    from .activity_log import log_activity
    from django.contrib.auth.models import User

    try:
        user = User.objects.get(id=user_id)

        time.sleep(5)
        order = Order.objects.get(id=order_id)
        order.status = "executed"
        order.save(update_fields=["status", "updated_at"])
        log_activity(user, "order_executed", {"order_id": order_id, "instrument": order.instrument})
        _broadcast_order_update(order, "order.executed")
        logger.info("Order %s -> executed", order_id)

        time.sleep(10)
        order.refresh_from_db()
        order.status = "closed"
        order.save(update_fields=["status", "updated_at"])
        log_activity(user, "order_closed", {"order_id": order_id, "instrument": order.instrument})
        _broadcast_order_update(order, "order.closed")
        logger.info("Order %s -> closed", order_id)

    except Exception as exc:
        logger.error("Lifecycle simulation failed for order %s: %s", order_id, exc)


def _broadcast_order_update(order, event_type: str):
    """Push an order status change to the user's WebSocket group."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("No channel layer configured, skipping broadcast")
            return

        group_name = f"orders_user_{order.user_id}"
        message = {
            "type": "order_update",
            "data": {
                "type": event_type,
                "order_id": str(order.id),
                "instrument": order.instrument,
                "action": order.action,
                "status": order.status,
                "entry_price": str(order.entry_price) if order.entry_price else None,
                "stop_loss": str(order.stop_loss),
                "take_profit": str(order.take_profit),
                "user": order.user.username,
            },
        }

        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.info("Broadcast %s for order %s", event_type, order.id)

    except Exception as exc:
        logger.warning("Failed to broadcast order update: %s", exc)
