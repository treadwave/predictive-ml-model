from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from app.core.security import hash_password, verify_password
from app.models.users import User


def create_user(db: Connection, email: str, password: str) -> dict | None:
    """Новый пользователь; None, если email уже занят."""
    query = (
        insert(User)
        .values(email=email, password_hash=hash_password(password))
        .on_conflict_do_nothing(index_elements=[User.email])
        .returning(User.id, User.email)
    )
    row = db.execute(query).mappings().first()
    db.commit()
    return dict(row) if row else None


def authenticate(db: Connection, email: str, password: str) -> dict | None:
    query = select(User.id, User.email, User.password_hash).where(User.email == email)
    row = db.execute(query).mappings().first()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"]}


def get_user(db: Connection, user_id: int) -> dict | None:
    row = db.execute(select(User.id, User.email).where(User.id == user_id)).mappings().first()
    return dict(row) if row else None
