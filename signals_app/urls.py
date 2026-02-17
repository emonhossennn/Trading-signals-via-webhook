"""
URL patterns for the signals_app.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path("health", views.health_check, name="health-check"),

    # Broker accounts
    path("accounts", views.create_account, name="create-account"),

    # Webhook
    path("webhook/receive-signal", views.receive_signal, name="receive-signal"),

    # Orders
    path("orders", views.list_orders, name="list-orders"),
    path("orders/<uuid:order_id>", views.get_order, name="get-order"),
]
