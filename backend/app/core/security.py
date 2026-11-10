import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import JWT_EXPIRE_MINUTES, JWT_SECRET

ALGORITHM = "HS256"
if len(JWT_SECRET.encode()) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 bytes; configure a persistent secret before starting the backend")
DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_token(user_id: int, token_version: int = 0) -> str:
    now = datetime.now(UTC)
    return jwt.encode({"sub": str(user_id), "ver": token_version, "iat": now,
                       "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES)}, JWT_SECRET, algorithm=ALGORITHM)


def identity_from_token(token: str) -> tuple[int, int] | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM],
                             options={"require": ["exp", "sub", "ver", "iat"]})
        if type(payload["ver"]) is not int or payload["ver"] < 0:
            return None
        return int(payload["sub"]), payload["ver"]
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None


def throttle_key(kind: str, value: str) -> str:
    return hmac.new(JWT_SECRET.encode(), f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()
