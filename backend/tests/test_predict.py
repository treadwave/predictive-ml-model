import numpy as np
import pytest
import xgboost as xgb
from app.models import MlPrediction
from app.services.equipment_service import SENSOR_CODES
from sqlalchemy import select


@pytest.fixture
def model(tmp_path, monkeypatch) -> xgb.Booster:
    x = np.random.default_rng(0).normal(size=(20, len(SENSOR_CODES)))
    y = np.linspace(0, 125, 20)
    booster = xgb.train({"objective": "reg:squarederror"},
                        xgb.DMatrix(x, label=y, feature_names=SENSOR_CODES), num_boost_round=3)
    path = tmp_path / "model.json"
    booster.save_model(path)
    monkeypatch.setenv("MODEL_PATH", str(path))
    return booster


def expected_rul(model: xgb.Booster, sensors: dict[str, float]) -> float:
    values = np.array([[sensors[code] for code in SENSOR_CODES]])
    return float(model.predict(xgb.DMatrix(values, feature_names=SENSOR_CODES))[0])


def stored_predictions(db, equipment_id: int) -> list[tuple[int, float]]:
    query = select(MlPrediction.cycle, MlPrediction.predicted_rul).where(MlPrediction.equipment_id == equipment_id)
    rows = db.execute(query).all()
    db.rollback()
    return [tuple(row) for row in rows]


def test_unknown_equipment(client):
    assert client.post("/predict", json={"equipment_id": 999}).status_code == 404


def test_without_readings_keeps_defaults(client, db, model, add_equipment):
    equipment_id = add_equipment()

    body = client.post("/predict", json={"equipment_id": equipment_id}).json()

    assert body["predicted_rul"] == 125
    assert stored_predictions(db, equipment_id) == []


def test_runs_inference_on_latest_reading(client, db, model, add_equipment, add_reading):
    equipment_id = add_equipment()
    add_reading(equipment_id, cycle=1)
    latest = add_reading(equipment_id, cycle=2)

    body = client.post("/predict", json={"equipment_id": equipment_id}).json()

    rul = expected_rul(model, latest)
    assert body["current_cycle"] == 2
    assert body["predicted_rul"] == pytest.approx(rul)
    assert stored_predictions(db, equipment_id) == [(2, pytest.approx(rul))]


def test_replaces_existing_prediction(client, db, model, add_equipment, add_prediction, add_reading):
    equipment_id = add_equipment()
    sensors = add_reading(equipment_id, cycle=1)
    add_prediction(equipment_id, cycle=1, rul=999)

    client.post("/predict", json={"equipment_id": equipment_id})

    assert stored_predictions(db, equipment_id) == [(1, pytest.approx(expected_rul(model, sensors)))]


def test_missing_model(client, add_equipment, add_reading, monkeypatch):
    equipment_id = add_equipment()
    add_reading(equipment_id, cycle=1)
    monkeypatch.setenv("MODEL_PATH", "/nonexistent/model.json")

    response = client.post("/predict", json={"equipment_id": equipment_id})

    assert response.status_code == 503
