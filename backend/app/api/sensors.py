from fastapi import APIRouter

from app.core.db import DB
from app.schemas.sensor import SensorOut
from app.services import sensor_service

router = APIRouter(prefix="/sensors", tags=["Справочники"])


@router.get("", response_model=list[SensorOut], summary="Каталог датчиков")
def list_sensors(db: DB):
    return sensor_service.list_sensors(db)
