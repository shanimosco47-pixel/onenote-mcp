"""
MSAL token cache backed by a Fernet-encrypted file on persistent disk.

The MSAL_CACHE_KEY env var holds the Fernet key (base64-encoded 32-byte key).
Tokens are NEVER written as plain JSON and NEVER logged.
"""

import os
import logging
from pathlib import Path

import msal
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(os.getenv("DATA_DIR", "/data")) / "token_cache.bin"


def _fernet() -> Fernet:
    raw_key = os.getenv("MSAL_CACHE_KEY", "")
    if not raw_key:
        raise EnvironmentError("MSAL_CACHE_KEY environment variable is not set")
    return Fernet(raw_key.encode())


def load_token_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if _CACHE_PATH.exists():
        try:
            encrypted = _CACHE_PATH.read_bytes()
            serialized = _fernet().decrypt(encrypted).decode("utf-8")
            cache.deserialize(serialized)
            logger.debug("Token cache loaded from disk")
        except InvalidToken:
            logger.error("Token cache decryption failed — cache may be corrupt or key changed")
        except Exception as exc:
            logger.error("Failed to load token cache: %s", exc)
    return cache


def save_token_cache(cache: msal.SerializableTokenCache) -> None:
    if not cache.has_state_changed:
        return
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        serialized = cache.serialize()
        encrypted = _fernet().encrypt(serialized.encode("utf-8"))
        _CACHE_PATH.write_bytes(encrypted)
        logger.debug("Token cache persisted to disk")
    except Exception as exc:
        logger.error("Failed to save token cache: %s", exc)


def clear_token_cache() -> None:
    if _CACHE_PATH.exists():
        _CACHE_PATH.unlink()
        logger.info("Token cache cleared from disk")


def build_msal_app(cache: msal.SerializableTokenCache) -> msal.ConfidentialClientApplication:
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    if not all([client_id, client_secret, tenant_id]):
        raise EnvironmentError("AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID must all be set")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
        token_cache=cache,
    )


SCOPES = ["https://graph.microsoft.com/Notes.Read", "offline_access"]
