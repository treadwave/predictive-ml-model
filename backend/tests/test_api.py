from datetime import datetime

import pytest
from app.models import Alert
from sqlalchemy import insert


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sensor_catalog(client):
    sensors = client.get("/sensors").json()

    assert [s["code"] for s in sensors] == [f"s{i}" for i in range(1, 22)]
    unused = [s["code"] for s in sensors if not s["is_used"]]
    assert unused == ["s1", "s5", "s6", "s10", "s16", "s18", "s19"]


def test_equipment_without_predictions_has_defaults(client, add_equipment):
    add_equipment()

    equipment = client.get("/equipment").json()[0]

    assert equipment["current_cycle"] == 0
    assert equipment["predicted_rul"] == 125
    assert equipment["status"] == "normal"


@pytest.mark.parametrize(("rul", "status"), [
    (76, "normal"),
    (75, "warning"),
    (31, "warning"),
    (30, "critical"),
])
def test_status_thresholds(client, add_equipment, add_prediction, rul, status):
    equipment_id = add_equipment()
    add_prediction(equipment_id, cycle=5, rul=rul)

    body = client.get(f"/equipment/{equipment_id}/status").json()

    assert body["status"] == status
    assert body["current_cycle"] == 5


def test_status_uses_latest_cycle(client, add_equipment, add_prediction):
    equipment_id = add_equipment()
    add_prediction(equipment_id, cycle=6, rul=20)
    add_prediction(equipment_id, cycle=5, rul=100)

    body = client.get(f"/equipment/{equipment_id}").json()

    assert body["predicted_rul"] == 20
    assert body["current_cycle"] == 6


@pytest.mark.parametrize("path", [
    "/equipment/999",
    "/equipment/999/status",
    "/equipment/999/history",
    "/equipment/999/forecast",
    "/alerts/999",
])
def test_unknown_equipment(client, path):
    assert client.get(path).status_code == 404


def test_history_filters_by_cycle(client, add_equipment, add_reading):
    equipment_id = add_equipment()
    for cycle in range(1, 6):
        add_reading(equipment_id, cycle)

    rows = client.get(f"/equipment/{equipment_id}/history?from_cycle=2&to_cycle=4").json()

    assert [row["cycle"] for row in rows] == [2, 3, 4]
    assert len(rows[0]["sensors"]) == 14


def test_history_limit_keeps_latest(client, add_equipment, add_reading):
    equipment_id = add_equipment()
    for cycle in range(1, 6):
        add_reading(equipment_id, cycle)

    rows = client.get(f"/equipment/{equipment_id}/history?limit=2").json()

    assert [row["cycle"] for row in rows] == [4, 5]


def test_history_rejects_inverted_range(client, add_equipment):
    equipment_id = add_equipment()

    response = client.get(f"/equipment/{equipment_id}/history?from_cycle=5&to_cycle=1")

    assert response.status_code == 400


def test_forecast_counts_down_to_failure(client, add_equipment, add_prediction):
    equipment_id = add_equipment()
    add_prediction(equipment_id, cycle=100, rul=10)

    forecast = client.get(f"/equipment/{equipment_id}/forecast").json()

    assert forecast["predicted_failure_cycle"] == 110
    assert [p["cycle"] for p in forecast["points"]] == list(range(100, 111))
    assert forecast["points"][0]["rul"] == 10
    assert forecast["points"][-1]["rul"] == 0
    assert all(p["rul_low"] <= p["rul"] <= p["rul_high"] for p in forecast["points"])


def test_alerts_filtered_by_equipment_newest_first(client, db, add_equipment):
    first, second = add_equipment(81), add_equipment(82)
    db.execute(insert(Alert), [
        {"equipment_id": first, "cycle": 1, "severity": "warning", "message": "old",
         "triggered_at": datetime(2026, 1, 1)},
        {"equipment_id": first, "cycle": 2, "severity": "critical", "message": "new",
         "triggered_at": datetime(2026, 1, 2)},
        {"equipment_id": second, "cycle": 1, "severity": "warning", "message": "other",
         "triggered_at": datetime(2026, 1, 3)},
    ])
    db.commit()

    alerts = client.get(f"/alerts/{first}").json()

    assert [a["message"] for a in alerts] == ["new", "old"]
    assert len(client.get("/alerts").json()) == 3
