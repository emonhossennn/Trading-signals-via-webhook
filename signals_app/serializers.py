"""
DRF serializers for request/response data.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import BrokerAccount, Order, ActivityLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "date_joined"]
        read_only_fields = fields


class BrokerAccountCreateSerializer(serializers.Serializer):
    """Payload for POST /accounts."""
    username = serializers.CharField(max_length=150)
    broker_name = serializers.CharField(max_length=100)
    account_id = serializers.CharField(max_length=100)
    api_key = serializers.CharField(write_only=True)


class BrokerAccountSerializer(serializers.ModelSerializer):
    """Read-only representation of a broker account (never exposes the key)."""
    class Meta:
        model = BrokerAccount
        fields = ["id", "broker_name", "account_id", "is_active", "created_at"]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id", "action", "instrument", "entry_price",
            "stop_loss", "take_profit", "status",
            "fake_order_id", "created_at", "updated_at",
        ]
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = ["id", "username", "action", "details", "timestamp"]
        read_only_fields = fields


class SignalWebhookSerializer(serializers.Serializer):
    """Incoming webhook payload."""
    signal = serializers.CharField(help_text="Raw signal text, e.g. 'BUY EURUSD @1.0860\\nSL 1.0850\\nTP 1.0890'")
