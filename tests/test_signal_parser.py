"""
Tests for the signal parser module.
"""

from django.test import TestCase
from signals_app.signal_parser import parse_signal, SignalValidationError


class SignalParserValidSignalsTest(TestCase):
    """Test parsing of well-formed trading signals."""

    def test_buy_with_entry_price(self):
        raw = "BUY EURUSD @1.0860\n\nSL 1.0850\nTP 1.0890"
        signal = parse_signal(raw)
        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.instrument, "EURUSD")
        self.assertAlmostEqual(signal.entry_price, 1.0860)
        self.assertAlmostEqual(signal.stop_loss, 1.0850)
        self.assertAlmostEqual(signal.take_profit, 1.0890)

    def test_sell_with_entry_price(self):
        raw = "SELL GBPUSD @1.2500\n\nSL 1.2550\nTP 1.2450"
        signal = parse_signal(raw)
        self.assertEqual(signal.action, "SELL")
        self.assertEqual(signal.instrument, "GBPUSD")
        self.assertAlmostEqual(signal.entry_price, 1.2500)
        self.assertAlmostEqual(signal.stop_loss, 1.2550)
        self.assertAlmostEqual(signal.take_profit, 1.2450)

    def test_buy_without_entry_price(self):
        """When no @price is given, entry_price should be None (market order)."""
        raw = "BUY XAUUSD\n\nSL 1900.50\nTP 1950.00"
        signal = parse_signal(raw)
        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.instrument, "XAUUSD")
        self.assertIsNone(signal.entry_price)
        self.assertAlmostEqual(signal.stop_loss, 1900.50)
        self.assertAlmostEqual(signal.take_profit, 1950.00)

    def test_buy_with_bracketed_entry_price(self):
        """[@price] form (as shown in the spec) should parse identically to @price."""
        raw = "BUY EURUSD [@1.0860]\nSL 1.0850\nTP 1.0890"
        signal = parse_signal(raw)
        self.assertEqual(signal.action, "BUY")
        self.assertAlmostEqual(signal.entry_price, 1.0860)

    def test_case_insensitive_action(self):
        raw = "buy eurusd\n\nsl 1.0850\ntp 1.0890"
        signal = parse_signal(raw)
        self.assertEqual(signal.action, "BUY")
        self.assertEqual(signal.instrument, "EURUSD")


class SignalParserInvalidSignalsTest(TestCase):
    """Test that invalid signals are properly rejected."""

    def test_empty_string(self):
        with self.assertRaises(SignalValidationError):
            parse_signal("")

    def test_missing_sl(self):
        raw = "BUY EURUSD @1.0860\n\nTP 1.0890"
        with self.assertRaises(SignalValidationError) as ctx:
            parse_signal(raw)
        self.assertIn("SL", str(ctx.exception))

    def test_missing_tp(self):
        raw = "BUY EURUSD @1.0860\n\nSL 1.0850"
        with self.assertRaises(SignalValidationError) as ctx:
            parse_signal(raw)
        self.assertIn("TP", str(ctx.exception))

    def test_invalid_action(self):
        raw = "HOLD EURUSD @1.0860\n\nSL 1.0850\nTP 1.0890"
        with self.assertRaises(SignalValidationError):
            parse_signal(raw)

    def test_buy_sl_higher_than_tp(self):
        """For BUY, SL must be lower than TP."""
        raw = "BUY EURUSD @1.0860\n\nSL 1.0900\nTP 1.0850"
        with self.assertRaises(SignalValidationError) as ctx:
            parse_signal(raw)
        self.assertIn("lower", str(ctx.exception))

    def test_sell_sl_lower_than_tp(self):
        """For SELL, SL must be higher than TP."""
        raw = "SELL EURUSD @1.0860\n\nSL 1.0800\nTP 1.0900"
        with self.assertRaises(SignalValidationError) as ctx:
            parse_signal(raw)
        self.assertIn("higher", str(ctx.exception))

    def test_too_few_lines(self):
        raw = "BUY EURUSD"
        with self.assertRaises(SignalValidationError):
            parse_signal(raw)

    def test_mismatched_bracket_rejected(self):
        """[@price without closing bracket must not silently pass."""
        raw = "BUY EURUSD [@1.0860\nSL 1.0850\nTP 1.0890"
        with self.assertRaises(SignalValidationError):
            parse_signal(raw)
