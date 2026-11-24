"""Rewarded-ad integration boundary.

Never trust the Mini App to tell the server that an ad was watched.
Only a provider's authenticated server-to-server callback may grant a reward.
"""
import hashlib
import hmac
from .config import settings

def verify_callback(raw_body: bytes, signature: str) -> bool:
    if not settings.ad_callback_secret or not signature:
        return False
    expected = hmac.new(settings.ad_callback_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
