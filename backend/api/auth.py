"""Login and bearer tokens.

Tokens are `<user>.<expiry>.<hmac>` signed with API_SECRET_KEY, so no session
table is needed. One admin account comes from the environment to start; a
user table can replace check_password later without changing the API.
"""

import hashlib
import hmac
import time


def check_password(settings, username, password):
    if not settings.admin_password:
        return False
    return hmac.compare_digest(username, settings.admin_user) and hmac.compare_digest(password, settings.admin_password)


def _sign(settings, payload):
    return hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(settings, username, now=None):
    expires = int((now or time.time()) + settings.token_hours * 3600)
    payload = f"{username}.{expires}"
    return f"{payload}.{_sign(settings, payload)}", expires


def verify_token(settings, token, now=None):
    """Returns the username for a valid token, else None."""
    if settings.service_token and hmac.compare_digest(token, settings.service_token):
        return "service"
    try:
        username, expires, signature = token.rsplit(".", 2)
        expires = int(expires)
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _sign(settings, f"{username}.{expires}")):
        return None
    if expires < (now or time.time()):
        return None
    return username
