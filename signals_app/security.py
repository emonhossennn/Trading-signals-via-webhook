"""
Security utilities for API key authentication and broker key encryption.
"""

import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using SHA-256 for secure storage and lookup.
    We never store raw API keys — only their hashes.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def encrypt_broker_key(plain_key: str) -> str:
    """
    Encrypt a broker API key using Fernet symmetric encryption.
    The encryption key is loaded from settings.ENCRYPTION_KEY.

    Returns the encrypted key as a string (base64-encoded).
    """
    encryption_key = settings.ENCRYPTION_KEY
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY is not configured in settings.")

    f = Fernet(encryption_key.encode("utf-8"))
    encrypted = f.encrypt(plain_key.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_broker_key(encrypted_key: str) -> str:
    """
    Decrypt a broker API key that was encrypted with encrypt_broker_key.

    Returns the original plain-text key.
    """
    encryption_key = settings.ENCRYPTION_KEY
    if not encryption_key:
        raise ValueError("ENCRYPTION_KEY is not configured in settings.")

    f = Fernet(encryption_key.encode("utf-8"))
    try:
        decrypted = f.decrypt(encrypted_key.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        logger.error("Failed to decrypt broker key — invalid token or wrong key")
        raise ValueError("Could not decrypt broker API key.")
