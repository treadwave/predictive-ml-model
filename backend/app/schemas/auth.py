from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PASSWORD_MAX_BYTES = 72
PASSWORD_MIN = 12


class PasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=72, repr=False)

    @field_validator("password", mode="before")
    @classmethod
    def fits_bcrypt(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
            size = 0
            limit = 0
            for character in value:
                size += len(character.encode("utf-8"))
                if size > PASSWORD_MAX_BYTES:
                    break
                limit += 1
            raise ValueError(f"Пароль слишком длинный. Сократите его до {limit} символов.")
        return value


class LoginIn(PasswordIn):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9._-]+$")

    @field_validator("login", mode="before")
    @classmethod
    def normalize_login(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value.isascii():
            raise ValueError("В логине разрешены только латинские буквы, цифры, точка, дефис и подчёркивание")
        return value.lower()


class CreateUserIn(LoginIn):
    password: str = Field(min_length=PASSWORD_MIN, max_length=72, repr=False)


class ResetPasswordIn(PasswordIn):
    password: str = Field(min_length=PASSWORD_MIN, max_length=72, repr=False)


class SetActiveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool = Field(strict=True)


class UserOut(BaseModel):
    id: int
    login: str
    role: Literal["admin", "employee"]
    is_active: bool


class ManagedUserOut(UserOut):
    created_at: datetime


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
