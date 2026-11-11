from sqlalchemy import Connection, and_, func, select

from app.core.config import RUL_CLIP, RUL_CRITICAL, RUL_WARNING
from app.models.equipment import Equipment
from app.models.ml_predictions import MlPrediction
from app.models.physics_predictions import PhysicsPrediction
from app.models.sensor_readings import SensorReading

SENSOR_CODES = ["s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"]


def status_from_rul(rul: float) -> str:
    if rul <= RUL_CRITICAL:
        return "critical"
    if rul <= RUL_WARNING:
        return "warning"
    return "normal"


def equipment_exists(db: Connection, equipment_id: int) -> bool:
    query = select(Equipment.id).where(Equipment.id == equipment_id)
    return db.execute(query).first() is not None


def _latest_predictions(db: Connection, equipment_id: int | None = None) -> list[dict]:
    """Оборудование + его последний прогноз (по максимальному циклу)."""
    last = (
        select(MlPrediction.equipment_id, func.max(MlPrediction.cycle).label("cycle"))
        .group_by(MlPrediction.equipment_id)
        .subquery()
    )

    query = (
        select(
            Equipment.id,
            Equipment.name,
            Equipment.type,
            Equipment.unit_number,
            Equipment.last_maintenance_date,
            MlPrediction.cycle.label("current_cycle"),
            MlPrediction.predicted_rul,
            MlPrediction.defect_probability,
            MlPrediction.residual,
        )
        .outerjoin(last, last.c.equipment_id == Equipment.id)
        .outerjoin(
            MlPrediction,
            and_(MlPrediction.equipment_id == last.c.equipment_id, MlPrediction.cycle == last.c.cycle),
        )
        .order_by(Equipment.id)
    )
    if equipment_id is not None:
        query = query.where(Equipment.id == equipment_id)

    items = []
    for row in db.execute(query).mappings():
        item = dict(row)
        if item["predicted_rul"] is None:
            item["current_cycle"] = 0
            item["predicted_rul"] = float(RUL_CLIP)
            item["defect_probability"] = 0.0
            item["residual"] = 0.0
        item["status"] = status_from_rul(item["predicted_rul"])
        items.append(item)
    return items


def _to_equipment_out(item: dict) -> dict:
    keys = ("id", "name", "type", "unit_number", "last_maintenance_date",
            "current_cycle", "status", "predicted_rul")
    return {k: item[k] for k in keys}


def list_equipment(db: Connection) -> list[dict]:
    return [_to_equipment_out(item) for item in _latest_predictions(db)]


def get_equipment(db: Connection, equipment_id: int) -> dict | None:
    items = _latest_predictions(db, equipment_id)
    return _to_equipment_out(items[0]) if items else None


def get_status(db: Connection, equipment_id: int) -> dict | None:
    items = _latest_predictions(db, equipment_id)
    if not items:
        return None
    e = items[0]
    return {
        "equipment_id": e["id"],
        "status": e["status"],
        "current_cycle": e["current_cycle"],
        "predicted_rul": e["predicted_rul"],
        "defect_probability": e["defect_probability"],
        "residual": e["residual"],
    }


def get_history(db: Connection, equipment_id: int, from_cycle: int | None, to_cycle: int | None,
                limit: int) -> list[dict] | None:
    if not equipment_exists(db, equipment_id):
        return None

    columns = [getattr(SensorReading, code) for code in SENSOR_CODES]
    query = select(SensorReading.cycle, *columns).where(SensorReading.equipment_id == equipment_id)
    if from_cycle is not None:
        query = query.where(SensorReading.cycle >= from_cycle)
    if to_cycle is not None:
        query = query.where(SensorReading.cycle <= to_cycle)
    query = query.order_by(SensorReading.cycle.desc()).limit(limit)

    rows = []
    for row in db.execute(query).mappings():
        sensors = {code: row[code] for code in SENSOR_CODES if row[code] is not None}
        rows.append({"cycle": row["cycle"], "sensors": sensors})
    rows.reverse()
    return rows


def get_physics(db: Connection, equipment_id: int, limit: int) -> list[dict] | None:
    if not equipment_exists(db, equipment_id):
        return None

    query = (
        select(PhysicsPrediction.cycle, PhysicsPrediction.predicted_degradation, MlPrediction.residual)
        .join(MlPrediction, and_(MlPrediction.equipment_id == PhysicsPrediction.equipment_id,
                                 MlPrediction.cycle == PhysicsPrediction.cycle))
        .where(PhysicsPrediction.equipment_id == equipment_id)
        .order_by(PhysicsPrediction.cycle.desc())
        .limit(limit)
    )

    points = [{"cycle": row.cycle, "expected": row.predicted_degradation,
               "actual": row.predicted_degradation + row.residual, "residual": row.residual}
              for row in db.execute(query)]
    points.reverse()
    return points


def get_forecast(db: Connection, equipment_id: int) -> dict | None:
    items = _latest_predictions(db, equipment_id)
    if not items:
        return None
    e = items[0]
    rul, cycle = e["predicted_rul"], e["current_cycle"]
    horizon = int(rul)
    points = []
    for k in range(horizon + 1):
        value, spread = rul - k, 2 + 0.12 * k
        points.append({"cycle": cycle + k, "rul": round(value, 1),
                       "rul_low": round(max(0.0, value - spread), 1), "rul_high": round(value + spread, 1)})
    return {"equipment_id": equipment_id, "current_cycle": cycle, "predicted_rul": rul,
            "predicted_failure_cycle": cycle + horizon, "points": points}
