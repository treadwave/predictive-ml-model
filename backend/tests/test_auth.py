import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest
from fastapi.routing import APIRoute
from sqlalchemy import insert, select, text, update

PASSWORD = "Correct-pass 123!"


def protected_routes():
    from main import app
    return sorted((method, re.sub(r"\{[^}]+\}", "1", route.path))
                  for route in app.routes if isinstance(route, APIRoute) and route.path not in ("/auth/login", "/health")
                  for method in route.methods)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def sign_in(client, login="worker", password=PASSWORD):
    return client.post("/auth/login", json={"login": login, "password": password})


def test_public_registration_removed(anon_client):
    assert anon_client.post("/auth/register", json={"login": "worker", "password": PASSWORD}).status_code == 404
    assert "/auth/register" not in anon_client.get("/openapi.json").json()["paths"]


@pytest.mark.parametrize(("method", "path"), protected_routes())
def test_every_api_requires_token(anon_client, method, path):
    response = anon_client.request(method, path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path"), [(method, path) for method, path in protected_routes()
                                               if path.startswith("/admin/")])
def test_employee_cannot_use_admin_api(client, method, path):
    assert client.request(method, path, json={"login": "intruder", "password": PASSWORD,
                                             "is_active": False}).status_code == 403


def test_create_and_login(admin_client, anon_client, db):
    response = admin_client.post("/admin/users", json={"login": "  Ivan.Petrov  ", "password": PASSWORD})
    assert response.status_code == 201
    user = response.json()
    assert user["login"] == "ivan.petrov" and user["role"] == "employee" and user["is_active"]
    assert "password_hash" not in user and "password" not in user
    hashed = db.execute(text("SELECT password_hash FROM users WHERE id=:id"), {"id": user["id"]}).scalar_one()
    assert hashed != PASSWORD and bcrypt.checkpw(PASSWORD.encode(), hashed.encode())
    login = sign_in(anon_client, "IVAN.PETROV")
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert anon_client.get("/auth/me", headers=bearer(token)).json()["login"] == "ivan.petrov"
    assert anon_client.get("/equipment", headers=bearer(token)).status_code == 200
    assert anon_client.get("/alerts", headers=bearer(token)).status_code == 200
    assert anon_client.get("/admin/users", headers=bearer(token)).status_code == 403


def test_admin_can_use_working_sections(admin_client, add_equipment, add_prediction, add_reading):
    equipment_id = add_equipment()
    add_reading(equipment_id, 1)
    add_prediction(equipment_id, 1, 100)
    for path in ("/equipment", f"/equipment/{equipment_id}", f"/equipment/{equipment_id}/history",
                 f"/equipment/{equipment_id}/forecast", "/alerts", "/auth/me", "/admin/users"):
        assert admin_client.get(path).status_code == 200, path
    assert admin_client.get("/auth/me").json()["role"] == "admin"


def test_duplicate_login_normalization(admin_client):
    assert admin_client.post("/admin/users", json={"login": "Employee", "password": PASSWORD}).status_code == 201
    assert admin_client.post("/admin/users", json={"login": " employee ", "password": PASSWORD}).status_code == 409


@pytest.mark.parametrize("login", ["", "ab", "a" * 65, "иван", "a b", "a@b.com", "adm\nin", "Kelvin", "foo/bar"])
def test_invalid_logins(admin_client, login):
    assert admin_client.post("/admin/users", json={"login": login, "password": PASSWORD}).status_code == 422


@pytest.mark.parametrize("password", ["Qx7!", "я" * 37, "a" * 73])
def test_invalid_passwords_never_echoed(admin_client, password):
    response = admin_client.post("/admin/users", json={"login": "worker", "password": password})
    assert response.status_code == 422
    assert password not in response.text
    assert all("input" not in error for error in response.json()["detail"])


def test_password_preserves_spaces_case_and_symbols(admin_client, anon_client):
    password = "  My Str0ng! Пароль  "
    assert admin_client.post("/admin/users", json={"login": "worker", "password": password}).status_code == 201
    assert sign_in(anon_client, password=password).status_code == 200
    assert sign_in(anon_client, password=password.strip()).status_code == 401
    assert sign_in(anon_client, password=password.lower()).status_code == 401


def test_cannot_inject_admin_role(admin_client, db):
    response = admin_client.post("/admin/users", json={"login": "worker", "password": PASSWORD, "role": "admin"})
    assert response.status_code == 422
    assert db.execute(text("SELECT count(*) FROM users WHERE login='worker'")).scalar_one() == 0


def test_bad_credentials_and_blocked_users_look_same(anon_client, account):
    account()
    account("disabled", is_active=False)
    responses = [sign_in(anon_client, login, password) for login, password in
                 [("worker", "wrong"), ("missing", PASSWORD), ("disabled", PASSWORD)]]
    assert all(response.status_code == 401 for response in responses)
    assert all(response.json() == {"detail": "Неверный логин или пароль"} for response in responses)


def test_reset_invalidates_all_old_tokens(admin_client, anon_client, account):
    user_id = account()
    old_tokens = [sign_in(anon_client).json()["access_token"] for _ in range(2)]
    response = admin_client.put(f"/admin/users/{user_id}/password", json={"password": "New password 456!"})
    assert response.status_code == 204
    assert sign_in(anon_client).status_code == 401
    for token in old_tokens:
        assert anon_client.get("/equipment", headers=bearer(token)).status_code == 401
    new_token = sign_in(anon_client, password="New password 456!").json()["access_token"]
    assert anon_client.get("/equipment", headers=bearer(new_token)).status_code == 200


def test_block_unblock_does_not_revive_token(admin_client, anon_client, account):
    user_id = account()
    old_token = sign_in(anon_client).json()["access_token"]
    assert admin_client.put(f"/admin/users/{user_id}/status", json={"is_active": False}).status_code == 200
    assert sign_in(anon_client).status_code == 401
    assert anon_client.get("/equipment", headers=bearer(old_token)).status_code == 401
    assert admin_client.put(f"/admin/users/{user_id}/status", json={"is_active": True}).status_code == 200
    assert anon_client.get("/equipment", headers=bearer(old_token)).status_code == 401
    assert sign_in(anon_client).status_code == 200


def test_reset_does_not_unblock(admin_client, anon_client, account):
    user_id = account(is_active=False)
    assert admin_client.put(f"/admin/users/{user_id}/password", json={"password": "New password 456!"}).status_code == 204
    assert sign_in(anon_client, password="New password 456!").status_code == 401


def test_admin_accounts_cannot_be_modified_from_panel(admin_client):
    user_id = admin_client.get("/auth/me").json()["id"]
    assert admin_client.put(f"/admin/users/{user_id}/status", json={"is_active": False}).status_code == 403
    assert admin_client.put(f"/admin/users/{user_id}/password", json={"password": PASSWORD}).status_code == 403
    assert admin_client.get("/admin/users").status_code == 200


def test_missing_account(admin_client):
    assert admin_client.put("/admin/users/999/password", json={"password": PASSWORD}).status_code == 404
    assert admin_client.put("/admin/users/999/status", json={"is_active": False}).status_code == 404


def test_role_loaded_from_database(admin_client, db):
    from app.models import User
    user_id = admin_client.get("/auth/me").json()["id"]
    db.execute(update(User).where(User.id == user_id).values(role="employee"))
    db.commit()
    assert admin_client.get("/admin/users").status_code == 403
    assert admin_client.get("/equipment").status_code == 200


def test_bad_and_legacy_tokens(anon_client, account):
    from app.core.config import JWT_SECRET
    user_id = account()
    payload = {"sub": str(user_id), "ver": 0, "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    tokens = ["garbage", jwt.encode(payload, "different-secret-for-test-0000000", algorithm="HS256"),
              jwt.encode({**payload, "exp": datetime.now(UTC) - timedelta(minutes=1)}, JWT_SECRET, algorithm="HS256"),
              jwt.encode({**payload, "sub": "999"}, JWT_SECRET, algorithm="HS256"),
              jwt.encode({k: v for k, v in payload.items() if k != "ver"}, JWT_SECRET, algorithm="HS256"),
              jwt.encode({**payload, "ver": True}, JWT_SECRET, algorithm="HS256")]
    for token in tokens:
        assert anon_client.get("/equipment", headers=bearer(token)).status_code == 401


def test_login_throttle_and_expiry(anon_client, db):
    from app.core.login_throttle import LOGIN_LIMIT
    for _ in range(LOGIN_LIMIT):
        assert sign_in(anon_client, password="wrong").status_code == 401
    blocked = sign_in(anon_client, "WORKER", "wrong")
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    db.execute(text("UPDATE login_attempts SET expires_at=now() - interval '1 second'"))
    db.commit()
    assert sign_in(anon_client, password="wrong").status_code == 401


def test_ip_limit_even_for_different_logins(anon_client, db):
    from app.core.login_throttle import IP_LIMIT
    from app.core.security import throttle_key
    from app.models.users import LoginAttempt
    db.execute(insert(LoginAttempt).values(key=throttle_key("ip", "testclient"), count=IP_LIMIT,
                                          expires_at=datetime.now(UTC) + timedelta(minutes=10)))
    db.commit()
    assert sign_in(anon_client, "another").status_code == 429


def test_concurrent_duplicate_creation(admin_client, db):
    def create(_):
        return admin_client.post("/admin/users", json={"login": "concurrent", "password": PASSWORD}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, range(2))) == [201, 409]
    assert db.execute(text("SELECT count(*) FROM users WHERE login='concurrent'")).scalar_one() == 1


def test_concurrent_reset_and_block_preserve_both_changes(admin_client, account, db):
    from app.models import User
    user_id = account()
    def reset():
        return admin_client.put(f"/admin/users/{user_id}/password", json={"password": "New password 456!"}).status_code
    def block():
        return admin_client.put(f"/admin/users/{user_id}/status", json={"is_active": False}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(reset), pool.submit(block)]
        assert [future.result() for future in futures] == [204, 200]
    user = db.execute(select(User).where(User.id == user_id)).mappings().one()
    assert not user["is_active"] and user["token_version"] == 2
    assert bcrypt.checkpw(b"New password 456!", user["password_hash"].encode())


def test_admin_cli(monkeypatch, anon_client, db):
    from app import create_admin
    monkeypatch.setattr("builtins.input", lambda _: "Bootstrap.Admin")
    monkeypatch.setattr(create_admin, "getpass", lambda _: PASSWORD)
    create_admin.main()
    login = sign_in(anon_client, "bootstrap.admin")
    assert login.status_code == 200 and login.json()["user"]["role"] == "admin"
    with pytest.raises(SystemExit, match="Логин уже занят"):
        create_admin.main()
    assert db.execute(text("SELECT count(*) FROM users")).scalar_one() == 1
