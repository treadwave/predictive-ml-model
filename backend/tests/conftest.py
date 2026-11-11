import os
import secrets
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, text

# Тесты очищают таблицы, поэтому БД для них задаётся отдельной переменной:
# рабочий DATABASE_URL здесь намеренно не используется.
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["RUL_WARNING"] = "75"
os.environ["RUL_CRITICAL"] = "30"
os.environ["RUL_CLIP"] = "125"
os.environ["JWT_SECRET"] = secrets.token_urlsafe(32)

TABLES = "alerts, ml_predictions, physics_predictions, sensor_readings, equipment, users"


@pytest.fixture
def db():
    from app.core.db import engine

    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    with engine.connect() as connection:
        yield connection


@pytest.fixture
def anon_client(db):
    from main import app

    return TestClient(app)


@pytest.fixture
def client(db):
    """Клиент вошедшего пользователя: все эндпоинты, кроме /auth, требуют токен."""
    from app.core.security import create_token
    from app.models import User
    from main import app

    statement = insert(User).values(email="operator@example.com", password_hash="-").returning(User.id)
    user_id = db.execute(statement).scalar_one()
    db.commit()
    return TestClient(app, headers={"Authorization": f"Bearer {create_token(user_id)}"})


@pytest.fixture
def add_equipment(db):
    from app.models import Equipment

    def add(unit_number: int = 81) -> int:
        statement = insert(Equipment).values(
            name=f"Turbofan №{unit_number}", type="turbofan", dataset="FD001",
            unit_number=unit_number, install_date=date(2024, 1, 1),
        )
        equipment_id = db.execute(statement.returning(Equipment.id)).scalar_one()
        db.commit()
        return equipment_id

    return add


@pytest.fixture
def add_prediction(db):
    from app.models import MlPrediction

    def add(equipment_id: int, cycle: int, rul: float) -> None:
        db.execute(insert(MlPrediction).values(
            equipment_id=equipment_id, cycle=cycle, predicted_rul=rul,
            defect_probability=0, residual=0, model_version="test",
        ))
        db.commit()

    return add


@pytest.fixture
def add_reading(db):
    from app.models import SensorReading
    from app.services.equipment_service import SENSOR_CODES

    def add(equipment_id: int, cycle: int) -> dict[str, float]:
        sensors = {code: float(i + cycle) for i, code in enumerate(SENSOR_CODES)}
        db.execute(insert(SensorReading).values(equipment_id=equipment_id, cycle=cycle, **sensors))
        db.commit()
        return sensors

    return add
