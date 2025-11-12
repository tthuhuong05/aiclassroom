# utils/hash_utils.py
"""
Shared utility functions for hashing quiz answers
"""
import hmac
import hashlib

def _hmac_secret():
    """Get the secret key for HMAC hashing"""
    try:
        from flask import current_app
        sk = (current_app.config.get("SECRET_KEY") or "dev-secret").encode("utf-8")
    except Exception:
        sk = b"dev-secret"
    return sk

def hash_option(text: str) -> str:
    """
    Hash an option text to create a secure hash for quiz answers.
    Uses the same secret key consistently across the application.
    """
    return hmac.new(_hmac_secret(), (text or "").encode("utf-8"), hashlib.sha256).hexdigest()[:16]

