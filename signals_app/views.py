"""
API views for the trading signal service.
"""

import logging
import secrets

from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.utils import timezone

from .authentication import APIKeyAuthentication
from .models import BrokerAccount, Order
from .serializers import (
    BrokerAccountCreateSerializer,
    BrokerAccountSerializer,
    OrderSerializer,
    SignalWebhookSerializer,
)
from .security import hash_api_key, encrypt_broker_key
from .activity_log import log_activity
from .signal_parser import parse_signal, SignalValidationError
from .mock_broker import execute_trade
from .order_manager import create_and_process_order

logger = logging.getLogger(__name__)


# ── Health Check ─────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check — returns 200 if the service is running."""
    return Response({
        "status": "ok",
        "timestamp": timezone.now().isoformat(),
    })


# ── Accounts ─────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([AllowAny])
def create_account(request):
    """
    Register a new user and link a broker account.

    Returns:
        - The user's API key (shown only once — must be saved by the user).
        - The linked broker account details.
    """
    serializer = BrokerAccountCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = request.data.get("username")
    if not username:
        return Response(
            {"error": "username is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if user already exists
    if User.objects.filter(username=username).exists():
        return Response(
            {"error": f"User '{username}' already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Generate an API key for the user
    raw_api_key = secrets.token_urlsafe(32)
    key_hash = hash_api_key(raw_api_key)

    # Create the Django user (store key hash in first_name for lookup)
    user = User.objects.create_user(
        username=username,
        password=None,  # No password needed — auth is via API key
        first_name=key_hash,
    )

    # Encrypt the broker API key and create the account
    encrypted_key = encrypt_broker_key(serializer.validated_data["api_key"])
    broker_account = BrokerAccount.objects.create(
        user=user,
        broker_name=serializer.validated_data["broker_name"],
        account_id=serializer.validated_data["account_id"],
        encrypted_api_key=encrypted_key,
    )

    log_activity(user, "account_created", {
        "broker_name": broker_account.broker_name,
        "account_id": broker_account.account_id,
    })

    return Response({
        "message": "Account created successfully.",
        "api_key": raw_api_key,  # Show only once!
        "user": {"id": user.id, "username": user.username},
        "broker_account": BrokerAccountSerializer(broker_account).data,
    }, status=status.HTTP_201_CREATED)


# ── Webhook ──────────────────────────────────────────────────

@api_view(["POST"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def receive_signal(request):
    """
    Receive a trading signal via webhook.

    Validates the signal, then processes it in the background
    (creates order, executes on mock broker, simulates lifecycle).
    """
    serializer = SignalWebhookSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    raw_signal = serializer.validated_data["signal"]

    log_activity(request.user, "signal_received", {"raw_signal": raw_signal})

    # Parse and validate the signal
    try:
        parsed = parse_signal(raw_signal)
    except SignalValidationError as e:
        log_activity(request.user, "signal_rejected", {
            "raw_signal": raw_signal,
            "reason": str(e),
        })
        return Response(
            {"error": str(e)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Find user's active broker account
    broker_account = BrokerAccount.objects.filter(
        user=request.user, is_active=True
    ).first()

    if not broker_account:
        return Response(
            {"error": "No active broker account found. Link one via POST /accounts first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Create order and kick off background lifecycle
    order = create_and_process_order(request.user, broker_account, parsed)

    return Response({
        "message": "Signal received. Order is being processed.",
        "order_id": str(order.id),
        "status": order.status,
    }, status=status.HTTP_200_OK)


# ── Orders ───────────────────────────────────────────────────

@api_view(["GET"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def list_orders(request):
    """Get all orders for the authenticated user."""
    orders = Order.objects.filter(user=request.user)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def get_order(request, order_id):
    """Get details of a single order by ID."""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Order not found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = OrderSerializer(order)
    return Response(serializer.data)
