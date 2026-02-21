import logging
import secrets

from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .authentication import APIKeyAuthentication
from .models import BrokerAccount, Order
from .serializers import (
    BrokerAccountCreateSerializer,
    BrokerAccountSerializer,
    OrderSerializer,
    SignalWebhookSerializer,
)
from .security import encrypt_broker_key, hash_api_key
from .activity_log import log_activity
from .signal_parser import SignalValidationError, parse_signal
from .order_manager import create_and_process_order

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Returns 200 if the service is up."""
    return Response({"status": "ok", "timestamp": timezone.now().isoformat()})


@api_view(["POST"])
@permission_classes([AllowAny])
def create_account(request):
    """
    Register a new user and link their broker account.

    The generated API key is returned once — the caller must save it.
    All subsequent requests authenticate via X-API-Key header.
    """
    serializer = BrokerAccountCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = serializer.validated_data["username"]

    if User.objects.filter(username=username).exists():
        return Response(
            {"error": f"Username '{username}' is already taken."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    raw_api_key = secrets.token_urlsafe(32)
    key_hash = hash_api_key(raw_api_key)

    # Store key hash in first_name for lookup — demo simplification;
    # a production system would use a dedicated APIKey model.
    user = User.objects.create_user(username=username, password=None, first_name=key_hash)

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
        "api_key": raw_api_key,
        "user": {"id": user.id, "username": user.username},
        "broker_account": BrokerAccountSerializer(broker_account).data,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def receive_signal(request):
    """
    Receive a trading signal via webhook.

    Validates and parses the signal, then hands it off to the order
    manager which persists the order and runs the lifecycle in the background.
    """
    serializer = SignalWebhookSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    raw_signal = serializer.validated_data["signal"]

    log_activity(request.user, "signal_received", {"raw_signal": raw_signal})

    try:
        parsed = parse_signal(raw_signal)
    except SignalValidationError as exc:
        log_activity(request.user, "signal_rejected", {
            "raw_signal": raw_signal,
            "reason": str(exc),
        })
        return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    broker_account = BrokerAccount.objects.filter(
        user=request.user, is_active=True
    ).first()

    if not broker_account:
        return Response(
            {"error": "No active broker account found. Link one via POST /accounts first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    order = create_and_process_order(request.user, broker_account, parsed)

    return Response({
        "message": "Signal received. Order is being processed.",
        "order_id": str(order.id),
        "status": order.status,
    }, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def list_orders(request):
    """Return all orders for the authenticated user, newest first."""
    orders = Order.objects.filter(user=request.user)
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def get_order(request, order_id):
    """Return a single order by UUID, scoped to the authenticated user."""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(OrderSerializer(order).data)


@api_view(["GET"])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsAuthenticated])
def get_analytics(request):
    """Simple performance stats: total trades and breakdown by instrument."""
    qs = Order.objects.filter(user=request.user)
    by_instrument = qs.values("instrument").annotate(count=Count("id"))
    return Response({
        "total_trades": qs.count(),
        "by_instrument": list(by_instrument),
    })
