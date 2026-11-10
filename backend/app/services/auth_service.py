from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from app.core.security import DUMMY_HASH, hash_password, verify_password
from app.models.users import User

PUBLIC_COLUMNS = (User.id, User.login, User.role, User.is_active, User.created_at)


def create_user(db: Connection, login: str, password: str, *, role: str = "employee") -> dict | None:
    row = db.execute(insert(User).values(login=login, password_hash=hash_password(password), role=role)
                     .on_conflict_do_nothing(index_elements=[User.login])
                     .returning(*PUBLIC_COLUMNS)).mappings().first()
    db.commit()
    return dict(row) if row else None


def authenticate(db: Connection, login: str, password: str) -> dict | None:
    row = db.execute(select(*PUBLIC_COLUMNS, User.password_hash, User.token_version)
                     .where(User.login == login)).mappings().first()
    # Always run bcrypt, including unknown logins and disabled accounts.
    valid = verify_password(password, row["password_hash"] if row else DUMMY_HASH)
    if row is None or not valid or not row["is_active"]:
        return None
    return {key: value for key, value in row.items() if key != "password_hash"}


def get_user(db: Connection, user_id: int) -> dict | None:
    row = db.execute(select(*PUBLIC_COLUMNS, User.token_version).where(User.id == user_id)).mappings().first()
    return dict(row) if row else None
