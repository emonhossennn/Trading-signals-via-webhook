"""
Database models for the trading signal service.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User


class BrokerAccount(models.Model):
    """
    Stores a user's linked broker account details.
    The API key is encrypted at rest using Fernet symmetric encryption.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="broker_accounts")
    broker_name = models.CharField(max_length=100, help_text="e.g. MetaTrader5, cTrader")
    account_id = models.CharField(max_length=100, help_text="Broker account identifier")
    encrypted_api_key = models.TextField(help_text="Fernet-encrypted broker API key")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.broker_name} - {self.account_id} ({self.user.username})"


class Order(models.Model):
    """
    Represents a trading order created from a parsed signal.
    Tracks the full lifecycle: pending -> executed -> closed.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("executed", "Executed"),
        ("closed", "Closed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    broker_account = models.ForeignKey(
        BrokerAccount, on_delete=models.SET_NULL, null=True, related_name="orders"
    )
    action = models.CharField(max_length=4, choices=[("BUY", "Buy"), ("SELL", "Sell")])
    instrument = models.CharField(max_length=20, help_text="e.g. EURUSD, XAUUSD")
    entry_price = models.DecimalField(
        max_digits=12, decimal_places=5, null=True, blank=True,
        help_text="None means executed at market price"
    )
    stop_loss = models.DecimalField(max_digits=12, decimal_places=5)
    take_profit = models.DecimalField(max_digits=12, decimal_places=5)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    fake_order_id = models.CharField(
        max_length=50, blank=True,
        help_text="Simulated order ID returned by the mock broker"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.instrument} [{self.status}]"



class ApiKey(models.Model):
    """
    Stores hashed API keys for authenticated access.
    A user can have multiple API keys.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    key_hash = models.CharField(max_length=128, db_index=True, help_text="Hashed version of the raw API key")
    label = models.CharField(max_length=100, blank=True, help_text="Friendly name for the key")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label or 'Key'} for {self.user.username}"


class ActivityLog(models.Model):

    """
    Tracks user activity and important system events for auditing.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="activity_logs"
    )
    action = models.CharField(max_length=100, help_text="e.g. signal_received, order_created")
    details = models.JSONField(default=dict, blank=True, help_text="Additional context as JSON")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        user_str = self.user.username if self.user else "system"
        return f"[{self.timestamp}] {user_str}: {self.action}"
