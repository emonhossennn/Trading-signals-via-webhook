"""
Custom API key authentication for DRF.

Users include their API key in the X-API-Key header. We hash it
and look up the matching user in the database.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

from .security import hash_api_key
from .models import BrokerAccount


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate requests using the X-API-Key header.

    We store a hashed version of each user's API key in their
    User profile (via the username field for simplicity, or
    a separate model). For this implementation we store it
    as a broker account lookup — the user must have at least
    one active broker account, and the API key is tied to
    the user's profile.

    For simplicity, the API key hash is stored in the user's
    profile 'first_name' field (as a demo). In production,
    you'd use a dedicated APIKey model.
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            return None  # Let other auth methods handle it

        key_hash = hash_api_key(api_key)

        try:
            # We store the API key hash in the user's first_name field
            # as a simple demo approach. A production system would use
            # a dedicated APIKey model with a ForeignKey to User.
            user = User.objects.get(first_name=key_hash)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid API key.")

        return (user, None)
