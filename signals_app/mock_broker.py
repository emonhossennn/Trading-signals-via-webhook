"""
Mock broker service.

Simulates executing trades on a broker platform.
In production, this would connect to MetaTrader or a real broker API.
"""

import uuid
import logging
from dataclasses import dataclass

from .signal_parser import ParsedSignal

logger = logging.getLogger(__name__)


@dataclass
class FakeOrderResult:
    """Result from the mock broker execution."""
    order_id: str
    success: bool
    message: str


def execute_trade(signal: ParsedSignal, user, broker_account) -> FakeOrderResult:
    """
    Simulate executing a trade on the user's broker account.

    In a real system, this would call the broker's API (e.g. MetaTrader 5).
    Here we just log the action and return a fake order ID.
    """
    fake_order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

    price_info = f"@{signal.entry_price}" if signal.entry_price else "@MARKET"

    logger.info(
        f"Executing {signal.action} {signal.instrument} {price_info} "
        f"for user {user.username} on {broker_account.broker_name} "
        f"(account: {broker_account.account_id}) → {fake_order_id}"
    )

    return FakeOrderResult(
        order_id=fake_order_id,
        success=True,
        message=f"{signal.action} {signal.instrument} executed successfully.",
    )
