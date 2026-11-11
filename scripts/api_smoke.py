import json
import re
import secrets
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
WAIT = int(sys.argv[2]) if len(sys.argv) > 2 else 240

CONTRACT = [
    ("GET", "/equipment"),
    ("GET", "/equipment/{id}"),
    ("GET", "/equipment/{id}/status"),
    ("GET", "/equipment/{id}/history"),
    ("GET", "/equipment/{id}/forecast"),
    ("GET", "/alerts"),
    ("GET", "/alerts/{id}"),
    ("POST", "/predict"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
]


def call(method, path, body=None, token=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        return e.code, None
    except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
        return None, None


def fail(msg):
    print(f"ОШИБКА: {msg}")
    sys.exit(1)


def wait_for(get_value, what):
    """Повторяет get_value() раз в 3 с, пока не вернёт не-None, но не дольше WAIT секунд."""
    deadline = time.time() + WAIT
    while time.time() < deadline:
        value = get_value()
        if value is not None:
            return value
        time.sleep(3)
    fail(f"за {WAIT} с не дождались: {what}")


def norm(path):
    return re.sub(r"\{[^}]+\}", "{}", path)


def main():
    schema = wait_for(lambda: (lambda r: r[1] if r[0] == 200 and isinstance(r[1], dict) else None)(
        call("GET", "/openapi.json")), "ответа /openapi.json")
    paths = {norm(p): {m.upper() for m in methods} for p, methods in schema.get("paths", {}).items()}

    prefix = next((p[: -len("/equipment")] for p in schema["paths"] if norm(p).endswith("/equipment")), None)
    if prefix is None:
        fail("в OpenAPI нет эндпоинта /equipment")

    missing = [f"{m} {prefix}{p}" for m, p in CONTRACT if m not in paths.get(norm(prefix + p), set())]
    if missing:
        fail("в API нет эндпоинтов из контракта README:\n  " + "\n  ".join(missing))
    print(f"OK  контракт README: {len(CONTRACT)} эндпоинтов найдено (префикс {prefix or '—'!r})")

    code, _ = call("GET", prefix + "/equipment")
    if code != 401:
        fail(f"без токена GET {prefix}/equipment: ожидали 401, получили {code}")
    print("OK  без токена -> 401")

    credentials = {"email": f"smoke-{int(time.time())}@example.com", "password": secrets.token_urlsafe(16)}
    code, session = call("POST", prefix + "/auth/register", credentials)
    if code != 201 or not isinstance(session, dict) or not session.get("access_token"):
        fail(f"регистрация: ожидали 201 с токеном, получили {code}")
    token = session["access_token"]
    print(f"OK  POST {prefix}/auth/register -> 201, токен получен")

    items = wait_for(lambda: (lambda r: r[1] if r[0] == 200 and isinstance(r[1], list) and r[1] else None)(
        call("GET", prefix + "/equipment", token=token)), "непустого списка оборудования (работают ли симулятор и воркер?)")
    if not isinstance(items[0], dict) or "id" not in items[0]:
        fail("у элементов /equipment нет поля id")
    eq_id = items[0]["id"]
    print(f"OK  GET {prefix}/equipment: {len(items)} шт.")

    for method, path in CONTRACT:
        if method != "GET" or path == "/equipment":
            continue
        real = prefix + path.replace("{id}", str(eq_id))
        wait_for(lambda real=real: True if call("GET", real, token=token)[0] == 200 else None, f"ответа 200 от GET {real}")
        print(f"OK  GET {real}")

    code, _ = call("GET", f"{prefix}/equipment/999999999", token=token)
    if code != 404:
        fail(f"несуществующее оборудование: ожидали 404, получили {code}")
    print("OK  несуществующее оборудование -> 404")
    print("Смоук-проверка API пройдена")


if __name__ == "__main__":
    main()
