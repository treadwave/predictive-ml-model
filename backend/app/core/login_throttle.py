from datetime import timedelta

from fastapi import HTTPException, Request
from sqlalchemy import case, delete, func
from sqlalchemy.dialects.postgresql import insert

from app.core.db import engine
from app.core.security import throttle_key
from app.models.users import LoginAttempt

WINDOW_SECONDS = 15 * 60
LOGIN_LIMIT = 10
IP_LIMIT = 60


def check_login_attempt(request: Request, login: str):
    """Atomic counters shared across workers. Count all attempts, before bcrypt.

    Use the actual peer address; do not trust client-supplied forwarding headers.
    Successful login does not reset limits, which would enable a bypass.
    """
    identities = [("login", login, LOGIN_LIMIT),
                  ("ip", request.client.host if request.client else "unknown", IP_LIMIT)]
    exceeded = False
    retry_after = 1
    with engine.begin() as db:
        db.execute(delete(LoginAttempt).where(LoginAttempt.expires_at <= func.now()))
        for kind, value, limit in identities:
            statement = insert(LoginAttempt).values(
                key=throttle_key(kind, value), count=1,
                expires_at=func.now() + timedelta(seconds=WINDOW_SECONDS),
            )
            expired = LoginAttempt.expires_at <= func.now()
            row = db.execute(statement.on_conflict_do_update(
                index_elements=[LoginAttempt.key],
                set_={"count": case((expired, 1), else_=LoginAttempt.count + 1),
                      "expires_at": case((expired, statement.excluded.expires_at), else_=LoginAttempt.expires_at)},
            ).returning(LoginAttempt.count,
                        func.extract("epoch", LoginAttempt.expires_at - func.now()).label("remaining"))).one()
            if row.count > limit:
                exceeded = True
                retry_after = max(retry_after, int(row.remaining) + 1)
    if exceeded:
        raise HTTPException(429, "Слишком много попыток входа. Повторите позже.",
                            headers={"Retry-After": str(retry_after)})
