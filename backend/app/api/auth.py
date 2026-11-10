from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import DB
from app.core.login_throttle import check_login_attempt
from app.core.security import create_token, identity_from_token
from app.schemas.auth import AuthOut, LoginIn, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Авторизация"])
bearer = HTTPBearer(auto_error=False, description="Токен из /auth/login")
UNAUTHORIZED = {401: {"description": "Требуется действующий токен активного пользователя"}}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict:
    identity = identity_from_token(credentials.credentials) if credentials else None
    user = auth_service.get_user(db, identity[0]) if identity else None
    if user is None or not user["is_active"] or user["token_version"] != identity[1]:
        raise _unauthorized("Требуется вход в систему")
    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Доступ разрешён только администратору")
    return user


@router.post("/login", response_model=AuthOut, responses={**UNAUTHORIZED, 429: {"description": "Лимит попыток входа"}},
             summary="Вход по логину и паролю")
def login(body: LoginIn, request: Request, db: DB):
    check_login_attempt(request, body.login)
    user = auth_service.authenticate(db, body.login, body.password)
    if user is None:
        raise _unauthorized("Неверный логин или пароль")
    return {"access_token": create_token(user["id"], user["token_version"]), "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut, responses=UNAUTHORIZED, summary="Текущий пользователь")
def me(user: CurrentUser):
    return user
