"""Run on the server: python -m app.create_admin (credentials are never command arguments)."""
from getpass import getpass

from pydantic import ValidationError

from app.core.db import engine
from app.schemas.auth import CreateUserIn
from app.services.auth_service import create_user


def main():
    try:
        login = input("Логин администратора: ")
        password = getpass("Пароль (от 12 символов): ")
        confirm = getpass("Повторите пароль: ")
        if password != confirm:
            raise SystemExit("Пароли не совпадают. Аккаунт не создан.")
        try:
            credentials = CreateUserIn(login=login, password=password)
        except ValidationError as exc:
            # Never print Pydantic's input values: they may include the password.
            raise SystemExit("; ".join(error["msg"] for error in exc.errors(include_input=False))) from None
        with engine.connect() as db:
            user = create_user(db, credentials.login, credentials.password, role="admin")
        if user is None:
            raise SystemExit("Логин уже занят. Существующий аккаунт не изменён.")
        print(f"Администратор {user['login']} создан.")
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("Создание отменено.") from None


if __name__ == "__main__":
    main()
