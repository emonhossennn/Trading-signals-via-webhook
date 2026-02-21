"""
Parses raw trading signal text into a validated ParsedSignal dataclass.
"""

import re
from dataclasses import dataclass
from typing import Optional


class SignalValidationError(Exception):
    """Raised when a signal is malformed or fails logical validation."""
    pass


@dataclass
class ParsedSignal:
    action: str                  # BUY or SELL
    instrument: str              # e.g. EURUSD, XAUUSD
    entry_price: Optional[float] # None -> market order
    stop_loss: float
    take_profit: float


def parse_signal(raw_text: str) -> ParsedSignal:
    """
    Parse a raw signal message and return a validated ParsedSignal.

    Accepted formats for the first line:
        BUY EURUSD            (market order)
        BUY EURUSD @1.0860
        BUY EURUSD [@1.0860]

    Followed by SL and TP lines in any order:
        SL 1.0850
        TP 1.0890

    Raises SignalValidationError on malformed input or invalid SL/TP logic.
    """
    if not raw_text or not raw_text.strip():
        raise SignalValidationError("Signal text is empty.")

    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]

    if len(lines) < 3:
        raise SignalValidationError(
            "Signal must have at least 3 lines: action, SL, and TP."
        )

    action_line = lines[0]

    # Match either @price or [@price] — not a mix of one bracket and not the other
    action_pattern = re.compile(
        r"^(BUY|SELL)\s+([A-Z0-9]+)(?:\s+(?:\[@([\d.]+)\]|@([\d.]+)))?$",
        re.IGNORECASE,
    )
    match = action_pattern.match(action_line)
    if not match:
        raise SignalValidationError(
            f"Bad action line: '{action_line}'. Expected: BUY/SELL INSTRUMENT [@price]"
        )

    action = match.group(1).upper()
    instrument = match.group(2).upper()
    # group(3) = bracketed form, group(4) = bare form
    entry_price_str = match.group(3) or match.group(4)
    entry_price = float(entry_price_str) if entry_price_str else None

    stop_loss = _extract_value(lines, "SL")
    take_profit = _extract_value(lines, "TP")

    if action == "BUY" and stop_loss >= take_profit:
        raise SignalValidationError(
            f"BUY signal: SL ({stop_loss}) must be lower than TP ({take_profit})."
        )
    if action == "SELL" and stop_loss <= take_profit:
        raise SignalValidationError(
            f"SELL signal: SL ({stop_loss}) must be higher than TP ({take_profit})."
        )

    return ParsedSignal(
        action=action,
        instrument=instrument,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )


def _extract_value(lines: list[str], label: str) -> float:
    """Return the numeric value following `label` (e.g. 'SL', 'TP')."""
    pattern = re.compile(rf"^{label}\s+([\d.]+)$", re.IGNORECASE)
    for line in lines:
        m = pattern.match(line)
        if m:
            return float(m.group(1))
    raise SignalValidationError(f"Missing {label} in signal.")
