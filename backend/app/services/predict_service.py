import os
from functools import lru_cache

import numpy as np
import xgboost as xgb
from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from app.core.errors import model_unavailable
from app.models.ml_predictions import MlPrediction
from app.models.sensor_readings import SensorReading
from app.services import equipment_service
from app.services.equipment_service import SENSOR_CODES

MODEL_VERSION = "first_xgboost_model"


@lru_cache(maxsize=1)
def _load_model(path: str) -> xgb.Booster:
    model = xgb.Booster()
    model.load_model(path)
    return model


def _predict_rul(sensors: list[float | None]) -> float:
    path = os.getenv("MODEL_PATH")
    if not path or not os.path.exists(path):
        raise model_unavailable()
    features = xgb.DMatrix(np.array([sensors], dtype=float), feature_names=SENSOR_CODES)
    return float(_load_model(path).predict(features)[0])


def run_prediction(db: Connection, equipment_id: int) -> dict | None:
    """Инференс по последнему показанию. Результат записывается в ml_predictions."""
    if not equipment_service.equipment_exists(db, equipment_id):
        return None

    columns = [getattr(SensorReading, code) for code in SENSOR_CODES]
    query = (
        select(SensorReading.cycle, *columns)
        .where(SensorReading.equipment_id == equipment_id)
        .order_by(SensorReading.cycle.desc())
        .limit(1)
    )
    reading = db.execute(query).mappings().first()

    if reading is not None:
        rul = _predict_rul([reading[code] for code in SENSOR_CODES])
        statement = insert(MlPrediction).values(
            equipment_id=equipment_id, cycle=reading["cycle"], predicted_rul=rul,
            defect_probability=0, residual=0, model_version=MODEL_VERSION,
        )
        db.execute(statement.on_conflict_do_update(
            index_elements=["equipment_id", "cycle"],
            set_={"predicted_rul": rul, "model_version": MODEL_VERSION},
        ))
        db.commit()

    return equipment_service.get_status(db, equipment_id)
