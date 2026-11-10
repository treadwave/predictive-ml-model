import logging
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import JWT_EXPIRE_MINUTES, JWT_SECRET

logger = logging.getLogger("security")

ALGORITHM = "HS256"

if JWT_SECRET:
    _secret = JWT_SECRET
else:
    _secret = secrets.token_urlsafe(32)
    logger.warning("JWT_SECRET не задан: сгенерирован временный ключ, после перезапуска backend войти придётся заново")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user_id: int) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires}, _secret, algorithm=ALGORITHM)


def user_id_from_token(token: str) -> int | None:
    """id пользователя из токена; None, если токен неверен или просрочен."""
    try:
        payload = jwt.decode(token, _secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub"]})
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
