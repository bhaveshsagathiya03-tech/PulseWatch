import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from app.core.config import settings


def new_id() -> str:
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return "pbkdf2_sha256$240000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode().rstrip("="),
        base64.urlsafe_b64encode(digest).decode().rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_project_key() -> str:
    return "pw_pub_" + secrets.token_urlsafe(30)


def hash_project_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def create_session_token(user_id: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + settings.session_ttl_hours * 3600}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.session_secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def read_session_token(token: str) -> str | None:
    try:
        body, signature = token.split(".", 1)
        expected = _b64(hmac.new(settings.session_secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return str(payload.get("sub"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
