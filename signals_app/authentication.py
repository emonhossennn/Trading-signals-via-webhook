"""
Custom API key authentication for DRF.

Users include their API key in the X-API-Key header. We hash it
and look up the matching user in the database.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

from .security import hash_api_key
from .models import ApiKey


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate requests using the X-API-Key header.
    We hash the provided key and look up the matching ApiKey record.
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            return None

        key_hash = hash_api_key(api_key)

        try:
            api_key_obj = ApiKey.objects.select_related("user").get(key_hash=key_hash)
            user = api_key_obj.user
        except ApiKey.DoesNotExist:
            raise AuthenticationFailed("Invalid API key.")

        return (user, None)

