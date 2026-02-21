"""
WebSocket URL routing for the signals_app.
"""

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/orders/<int:user_id>", consumers.OrderConsumer.as_asgi()),
]
