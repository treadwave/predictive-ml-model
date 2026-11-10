import re
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi.routing import APIRoute
from sqlalchemy import text

OPEN_PATHS = {"/auth/register", "/auth/login", "/health"}
CREDENTIALS = {"email": "operator@example.com", "password": "correct-horse"}


def protected_routes() -> list[tuple[str, str]]:
    from main import app

    return sorted(
        (method, re.sub(r"\{[^}]+\}", "1", route.path))
        for route in app.routes
        if isinstance(route, APIRoute) and route.path not in OPEN_PATHS
        for method in route.methods
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_working_token(anon_client):
    response = anon_client.post("/auth/register", json={**CREDENTIALS, "email": " Operator@Example.COM "})

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "operator@example.com"

    me = anon_client.get("/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json() == body["user"]


def test_password_is_stored_as_bcrypt_hash(anon_client, db):
    anon_client.post("/auth/register", json=CREDENTIALS)

    stored = db.execute(text("SELECT password_hash FROM users")).scalar_one()

    assert CREDENTIALS["password"] not in stored
    assert bcrypt.checkpw(CREDENTIALS["password"].encode(), stored.encode())


def test_register_same_email_conflicts(anon_client):
    assert anon_client.post("/auth/register", json=CREDENTIALS).status_code == 201

    response = anon_client.post("/auth/register", json={**CREDENTIALS, "email": "OPERATOR@example.com"})

    assert response.status_code == 409


@pytest.mark.parametrize("payload", [
    {"email": "not-an-email", "password": "correct-horse"},
    {"email": "operator@example.com", "password": "short"},
    {"email": "operator@example.com", "password": "я" * 37},  # 74 байта — больше лимита bcrypt
    {"email": "operator@example.com"},
])
def test_register_validates_input(anon_client, payload):
    assert anon_client.post("/auth/register", json=payload).status_code == 422


def test_login_returns_working_token(anon_client):
    anon_client.post("/auth/register", json=CREDENTIALS)

    response = anon_client.post("/auth/login", json={**CREDENTIALS, "email": "Operator@example.com"})

    assert response.status_code == 200
    assert anon_client.get("/equipment", headers=bearer(response.json()["access_token"])).status_code == 200


@pytest.mark.parametrize("credentials", [
    {**CREDENTIALS, "password": "wrong-password"},
    {**CREDENTIALS, "email": "nobody@example.com"},
])
def test_login_rejects_wrong_credentials(anon_client, credentials):
    anon_client.post("/auth/register", json=CREDENTIALS)

    response = anon_client.post("/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль"


@pytest.mark.parametrize(("method", "path"), protected_routes())
def test_api_requires_token(anon_client, method, path):
    response = anon_client.request(method, path)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_protected_routes_cover_api():
    routes = protected_routes()

    assert ("GET", "/equipment") in routes
    assert ("GET", "/auth/me") in routes


def test_signed_in_client_reaches_api(client):
    assert client.get("/equipment").status_code == 200
    assert client.get("/auth/me").json()["email"] == "operator@example.com"


def _token(secret: str, sub: str = "1", minutes: int = 5) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": expires}, secret, algorithm="HS256")


def test_rejects_bad_tokens(client):
    from app.core.config import JWT_SECRET

    user_token = client.headers["Authorization"].removeprefix("Bearer ")
    user_id = jwt.decode(user_token, JWT_SECRET, algorithms=["HS256"])["sub"]
    bad = {
        "garbage": bearer("garbage"),
        "foreign secret": bearer(_token("another-secret-another-secret-0123", user_id)),
        "expired": bearer(_token(JWT_SECRET, user_id, minutes=-1)),
        "unknown user": bearer(_token(JWT_SECRET, "999")),
        "basic scheme": {"Authorization": f"Basic {user_token}"},
    }

    for name, headers in bad.items():
        response = client.get("/equipment", headers=headers)
        assert response.status_code == 401, name
