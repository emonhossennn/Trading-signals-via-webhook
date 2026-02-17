"""
Signal parser module.

Parses raw trading signal text messages into structured data
and validates them before they're sent to the broker.
"""

import re
from dataclasses import dataclass
from typing import Optional


class SignalValidationError(Exception):
    """Raised when a trading signal fails validation."""
    pass


@dataclass
class ParsedSignal:
    """Structured representation of a parsed trading signal."""
    action: str          # BUY or SELL
    instrument: str      # e.g. EURUSD
    entry_price: Optional[float]  # None means market order
    stop_loss: float
    take_profit: float


def parse_signal(raw_text: str) -> ParsedSignal:
    """
    Parse a raw signal text message and return a validated ParsedSignal.

    Expected format:
        BUY EURUSD [@1.0860]
        SL 1.0850
        TP 1.0890

    The entry price (prefixed with @) is optional — if missing,
    the order should be executed at the current market price.

    Raises:
        SignalValidationError: If the signal text is malformed or
            fails logical validation (e.g. SL > TP for a BUY).
    """
    if not raw_text or not raw_text.strip():
        raise SignalValidationError("Signal text is empty.")

    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]

    if len(lines) < 3:
        raise SignalValidationError(
            "Signal must have at least 3 lines: action line, SL, and TP."
        )

    # --- Parse the first line: action, instrument, optional price ---
    action_line = lines[0]
    action_pattern = re.compile(
        r"^(BUY|SELL)\s+([A-Z0-9]+)(?:\s+@([\d.]+))?$",
        re.IGNORECASE,
    )
    match = action_pattern.match(action_line)
    if not match:
        raise SignalValidationError(
            f"Invalid action line: '{action_line}'. "
            "Expected format: BUY/SELL INSTRUMENT [@price]"
        )

    action = match.group(1).upper()
    instrument = match.group(2).upper()
    entry_price_str = match.group(3)

    entry_price = None
    if entry_price_str:
        try:
            entry_price = float(entry_price_str)
        except ValueError:
            raise SignalValidationError(
                f"Entry price '{entry_price_str}' is not a valid number."
            )

    # --- Parse SL and TP from remaining lines ---
    stop_loss = _extract_value(lines, "SL")
    take_profit = _extract_value(lines, "TP")

    # --- Validate SL/TP logic ---
    if action == "BUY":
        if stop_loss >= take_profit:
            raise SignalValidationError(
                f"For a BUY signal, SL ({stop_loss}) must be lower than TP ({take_profit})."
            )
    elif action == "SELL":
        if stop_loss <= take_profit:
            raise SignalValidationError(
                f"For a SELL signal, SL ({stop_loss}) must be higher than TP ({take_profit})."
            )

    return ParsedSignal(
        action=action,
        instrument=instrument,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )


def _extract_value(lines: list[str], label: str) -> float:
    """
    Find a line starting with the given label (e.g. 'SL', 'TP')
    and return the numeric value that follows it.

    Raises:
        SignalValidationError: If the label is not found or the
            value is not a valid number.
    """
    pattern = re.compile(rf"^{label}\s+([\d.]+)$", re.IGNORECASE)

    for line in lines:
        match = pattern.match(line)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                raise SignalValidationError(
                    f"{label} value '{match.group(1)}' is not a valid number."
                )

    raise SignalValidationError(f"Missing {label} value in signal.")
