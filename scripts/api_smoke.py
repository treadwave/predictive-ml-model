import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
WAIT = int(sys.argv[2]) if len(sys.argv) > 2 else 240
TOKEN = None

CONTRACT = [
    ("GET", "/equipment"),
    ("GET", "/equipment/{id}"),
    ("GET", "/equipment/{id}/status"),
    ("GET", "/equipment/{id}/history"),
    ("GET", "/equipment/{id}/forecast"),
    ("GET", "/equipment/{id}/physics"),
    ("GET", "/alerts"),
    ("GET", "/alerts/{id}"),
    ("POST", "/predict"),
]


def call(method, path, data=None, *, authenticated=True):
    headers = {"Accept": "application/json"}
    if authenticated and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
                                 data=json.dumps(data).encode() if data is not None else None)
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
    global TOKEN
    def get_schema():
        code, body = call("GET", "/openapi.json")
        return body if code == 200 and isinstance(body, dict) else None

    schema = wait_for(get_schema, "ответа /openapi.json")
    paths = {norm(p): {m.upper() for m in methods} for p, methods in schema.get("paths", {}).items()}

    prefix = next((p[: -len("/equipment")] for p in schema["paths"] if norm(p).endswith("/equipment")), None)
    if prefix is None:
        fail("в OpenAPI нет эндпоинта /equipment")

    missing = [f"{m} {prefix}{p}" for m, p in CONTRACT if m not in paths.get(norm(prefix + p), set())]
    if missing:
        fail("в API нет эндпоинтов из контракта README:\n  " + "\n  ".join(missing))
    print(f"OK  контракт README: {len(CONTRACT)} эндпоинтов найдено (префикс {prefix or '—'!r})")

    password = os.getenv("SMOKE_PASSWORD")
    if not password:
        fail("задайте SMOKE_PASSWORD для отдельного тестового аккаунта ci.smoke")
    code, session = call("POST", "/auth/login", {"login": "ci.smoke", "password": password}, authenticated=False)
    if code != 200 or not isinstance(session, dict) or not session.get("access_token"):
        fail(f"вход тестового пользователя: ожидали 200, получили {code}")
    TOKEN = session["access_token"]
    for method, path in CONTRACT:
        code, _ = call(method, prefix + path.replace("{id}", "1"), authenticated=False)
        if code != 401:
            fail(f"API без токена: ожидали 401 от {method} {path}, получили {code}")
    code, _ = call("GET", "/admin/users")
    if code != 403:
        fail(f"админка для сотрудника: ожидали 403, получили {code}")
    code, _ = call("POST", "/auth/register", {"login": "forbidden", "password": password}, authenticated=False)
    if code != 404:
        fail(f"публичная регистрация: ожидали 404, получили {code}")
    print("OK  вход, защита API, права сотрудника и отсутствие публичной регистрации")

    def get_equipment():
        code, body = call("GET", prefix + "/equipment")
        return body if code == 200 and isinstance(body, list) and body else None

    items = wait_for(get_equipment, "непустого списка оборудования (работают ли симулятор и воркер?)")
    if not isinstance(items[0], dict) or "id" not in items[0]:
        fail("у элементов /equipment нет поля id")
    eq_id = items[0]["id"]
    print(f"OK  GET {prefix}/equipment: {len(items)} шт.")

    for method, path in CONTRACT:
        if method != "GET" or path == "/equipment":
            continue
        real = prefix + path.replace("{id}", str(eq_id))
        wait_for(lambda real=real: True if call("GET", real)[0] == 200 else None, f"ответа 200 от GET {real}")
        print(f"OK  GET {real}")

    code, _ = call("GET", f"{prefix}/equipment/999999999")
    if code != 404:
        fail(f"несуществующее оборудование: ожидали 404, получили {code}")
    print("OK  несуществующее оборудование -> 404")
    print("Смоук-проверка API пройдена")


if __name__ == "__main__":
    main()
