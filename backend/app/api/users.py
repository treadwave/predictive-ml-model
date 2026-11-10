from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update

from app.api.auth import require_admin
from app.core.db import DB
from app.core.security import hash_password
from app.models.users import User
from app.schemas.auth import CreateUserIn, ManagedUserOut, ResetPasswordIn, SetActiveIn
from app.services.auth_service import PUBLIC_COLUMNS, create_user

router = APIRouter(prefix="/admin/users", tags=["Управление аккаунтами"], dependencies=[Depends(require_admin)],
                   responses={401: {"description": "Требуется вход"}, 403: {"description": "Недостаточно прав"}})


@router.get("", response_model=list[ManagedUserOut])
def list_users(db: DB, limit: Annotated[int, Query(ge=1, le=100)] = 50,
               offset: Annotated[int, Query(ge=0)] = 0):
    return db.execute(select(*PUBLIC_COLUMNS).order_by(User.id).limit(limit).offset(offset)).mappings().all()


@router.post("", response_model=ManagedUserOut, status_code=201)
def add_user(body: CreateUserIn, db: DB):
    user = create_user(db, body.login, body.password)
    if user is None:
        raise HTTPException(409, "Этот логин уже занят")
    return user


def employee_for_update(db: DB, user_id: int):
    user = db.execute(select(User.id, User.role).where(User.id == user_id).with_for_update()).mappings().first()
    if user is None:
        raise HTTPException(404, "Пользователь не найден")
    if user["role"] != "employee":
        raise HTTPException(403, "Через панель можно изменять только аккаунты сотрудников")


@router.put("/{user_id}/password", status_code=204)
def reset_password(user_id: int, body: ResetPasswordIn, db: DB):
    password_hash = hash_password(body.password)
    employee_for_update(db, user_id)
    db.execute(update(User).where(User.id == user_id).values(
        password_hash=password_hash, token_version=User.token_version + 1))
    db.commit()


@router.put("/{user_id}/status", response_model=ManagedUserOut)
def set_active(user_id: int, body: SetActiveIn, db: DB):
    employee_for_update(db, user_id)
    # Invalidate tokens even on repeated status updates; unblocking never revives old tokens.
    user = db.execute(update(User).where(User.id == user_id).values(
        is_active=body.is_active, token_version=User.token_version + 1,
    ).returning(*PUBLIC_COLUMNS)).mappings().one()
    db.commit()
    return user
