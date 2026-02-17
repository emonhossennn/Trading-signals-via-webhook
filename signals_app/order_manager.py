"""
Order manager.

Handles order creation, mock broker execution, and lifecycle simulation.
Uses threading to simulate background status transitions without
requiring Celery or an external task queue.
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
    Create an order from a parsed signal, execute on mock broker,
    and start the lifecycle simulation in a background thread.
    """
    # Execute on mock broker first
    result = execute_trade(signal, user, broker_account)

    # Create the order record
    order = Order.objects.create(
        user=user,
        broker_account=broker_account,
        action=signal.action,
        instrument=signal.instrument,
        entry_price=Decimal(str(signal.entry_price)) if signal.entry_price else None,
        stop_loss=Decimal(str(signal.stop_loss)),
        take_profit=Decimal(str(signal.take_profit)),
        status="pending",
        fake_order_id=result.order_id,
    )

    log_activity(user, "order_created", {
        "order_id": str(order.id),
        "action": signal.action,
        "instrument": signal.instrument,
        "fake_order_id": result.order_id,
    })

    # Kick off lifecycle simulation in a background thread
    thread = threading.Thread(
        target=_simulate_order_lifecycle,
        args=(str(order.id), user.id),
        daemon=True,
    )
    thread.start()

    return order


def _simulate_order_lifecycle(order_id: str, user_id: int):
    """
    Simulate the order lifecycle in the background:
      pending → (5s) → executed → (10s) → closed

    Each status change is broadcast via the WebSocket channel layer.
    """
    import django
    django.setup()

    from .models import Order
    from .activity_log import log_activity
    from django.contrib.auth.models import User

    try:
        user = User.objects.get(id=user_id)

        # Wait 5 seconds, then mark as executed
        time.sleep(5)
        order = Order.objects.get(id=order_id)
        order.status = "executed"
        order.save(update_fields=["status", "updated_at"])

        log_activity(user, "order_executed", {
            "order_id": order_id,
            "instrument": order.instrument,
        })
        _broadcast_order_update(order, "order.executed")
        logger.info(f"Order {order_id} → executed")

        # Wait 10 more seconds, then mark as closed
        time.sleep(10)
        order.refresh_from_db()
        order.status = "closed"
        order.save(update_fields=["status", "updated_at"])

        log_activity(user, "order_closed", {
            "order_id": order_id,
            "instrument": order.instrument,
        })
        _broadcast_order_update(order, "order.closed")
        logger.info(f"Order {order_id} → closed")

    except Exception as e:
        logger.error(f"Error in order lifecycle simulation for {order_id}: {e}")


def _broadcast_order_update(order, event_type: str):
    """
    Send an order status update to connected WebSocket clients
    via Django Channels' channel layer.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning("No channel layer configured — skipping broadcast")
            return

        # Broadcast to the global 'orders_updates' group (simple dashboard approach)
        group_name = "orders_updates"
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
        logger.info(f"Broadcast {event_type} for order {order.id}")

    except Exception as e:
        logger.warning(f"Failed to broadcast order update: {e}")
