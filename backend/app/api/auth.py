from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.db import DB
from app.core.security import create_token, user_id_from_token
from app.schemas.auth import AuthOut, LoginIn, RegisterIn, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Авторизация"])

bearer = HTTPBearer(auto_error=False, description="Токен из /auth/login или /auth/register")

UNAUTHORIZED = {401: {"description": "Нет токена, токен неверен или просрочен"}}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict:
    user_id = user_id_from_token(credentials.credentials) if credentials else None
    user = auth_service.get_user(db, user_id) if user_id is not None else None
    if user is None:
        raise _unauthorized("Требуется вход в систему")
    return user


def _session(user: dict) -> dict:
    return {"access_token": create_token(user["id"]), "token_type": "bearer", "user": user}


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED,
             responses={409: {"description": "Email уже зарегистрирован"}}, summary="Регистрация")
def register(body: RegisterIn, db: DB):
    user = auth_service.create_user(db, body.email, body.password)
    if user is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже зарегистрирован")
    return _session(user)


@router.post("/login", response_model=AuthOut, responses=UNAUTHORIZED, summary="Вход по email и паролю")
def login(body: LoginIn, db: DB):
    user = auth_service.authenticate(db, body.email, body.password)
    if user is None:
        raise _unauthorized("Неверный email или пароль")
    return _session(user)


@router.get("/me", response_model=UserOut, responses=UNAUTHORIZED, summary="Текущий пользователь")
def me(user: Annotated[dict, Depends(get_current_user)]):
    return user
