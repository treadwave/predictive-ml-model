import pytest
from sqlalchemy import insert


@pytest.fixture
def add_physics(db):
    from app.models import MlPrediction, PhysicsPrediction

    def add(equipment_id: int, cycle: int, expected: float, residual: float) -> None:
        db.execute(insert(PhysicsPrediction).values(
            equipment_id=equipment_id, cycle=cycle, predicted_degradation=expected,
        ))
        db.execute(insert(MlPrediction).values(
            equipment_id=equipment_id, cycle=cycle, predicted_rul=100,
            defect_probability=0, residual=residual, model_version="test",
        ))
        db.commit()

    return add


def test_physics_returns_expected_actual_and_residual(client, add_equipment, add_physics):
    equipment_id = add_equipment()
    add_physics(equipment_id, 2, expected=0.2, residual=-0.05)
    add_physics(equipment_id, 1, expected=0.1, residual=0.05)

    response = client.get(f"/equipment/{equipment_id}/physics")

    assert response.status_code == 200
    points = response.json()
    assert [p["cycle"] for p in points] == [1, 2]
    assert points[0]["expected"] == pytest.approx(0.1)
    assert points[0]["actual"] == pytest.approx(0.15)
    assert points[0]["residual"] == pytest.approx(0.05)
    assert points[1]["actual"] == pytest.approx(0.15)


def test_physics_limit_keeps_latest_cycles(client, add_equipment, add_physics):
    equipment_id = add_equipment()
    for cycle in (1, 2, 3):
        add_physics(equipment_id, cycle, expected=cycle / 10, residual=0)

    response = client.get(f"/equipment/{equipment_id}/physics", params={"limit": 2})

    assert [p["cycle"] for p in response.json()] == [2, 3]


def test_physics_is_empty_before_worker(client, add_equipment, add_reading):
    equipment_id = add_equipment()
    add_reading(equipment_id, 1)

    response = client.get(f"/equipment/{equipment_id}/physics")

    assert response.status_code == 200
    assert response.json() == []


def test_physics_unknown_equipment(client, db):
    response = client.get("/equipment/999/physics")

    assert response.status_code == 404
