"""
Tests for WebSocket functionality.
"""

import pytest
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from config.asgi import application


@pytest.mark.asyncio
class TestWebSocket:
    async def test_websocket_connect(self):
        """Test that a client can connect to the websocket endpoint."""
        communicator = WebsocketCommunicator(application, "/ws/orders")
        connected, subprotocol = await communicator.connect()
        assert connected

        # Check for connection message
        response = await communicator.receive_json_from()
        assert response["type"] == "connection_established"

        await communicator.disconnect()

    async def test_order_broadcast(self):
        """Test that the consumer receives broadcasts from the channel layer."""
        communicator = WebsocketCommunicator(application, "/ws/orders")
        await communicator.connect()
        
        # Consume the connection message first
        await communicator.receive_json_from()

        # Simulate a broadcast from the order manager
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "orders_updates",
            {
                "type": "order_update",
                "data": {
                    "type": "order.executed",
                    "order_id": "test-123",
                    "status": "executed"
                }
            }
        )

        # Check if the consumer forwarded it to the client
        response = await communicator.receive_json_from()
        assert response["type"] == "order.executed"
        assert response["order_id"] == "test-123"
        assert response["status"] == "executed"

        await communicator.disconnect()
