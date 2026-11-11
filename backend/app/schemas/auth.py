from pydantic import BaseModel, Field, field_validator

PASSWORD_MAX_BYTES = 72  # bcrypt не принимает пароли длиннее


class LoginIn(BaseModel):
    email: str = Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", examples=["operator@example.com"])
    password: str = Field(min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > PASSWORD_MAX_BYTES:
            raise ValueError(f"пароль длиннее {PASSWORD_MAX_BYTES} байт")
        return value


class RegisterIn(LoginIn):
    password: str = Field(min_length=8, description="От 8 символов, не длиннее 72 байт в UTF-8")


class UserOut(BaseModel):
    id: int
    email: str


class AuthOut(BaseModel):
    access_token: str = Field(description="JWT для заголовка Authorization: Bearer")
    token_type: str = "bearer"
    user: UserOut
