from fastapi import APIRouter, HTTPException, Query

from app.core.db import DB
from app.core.errors import NOT_FOUND, equipment_not_found
from app.schemas.equipment import (
    EquipmentOut,
    ForecastOut,
    PhysicsPointOut,
    ReadingOut,
    StatusOut,
)
from app.services import equipment_service

router = APIRouter(prefix="/equipment", tags=["Оборудование"])


def _found(value, equipment_id: int):
    if value is None:
        raise equipment_not_found(equipment_id)
    return value


@router.get("", response_model=list[EquipmentOut], summary="Список всех единиц оборудования")
def list_equipment(db: DB):
    return equipment_service.list_equipment(db)


@router.get("/{equipment_id}", response_model=EquipmentOut, responses=NOT_FOUND,
            summary="Информация об одной единице")
def get_equipment(equipment_id: int, db: DB):
    return _found(equipment_service.get_equipment(db, equipment_id), equipment_id)


@router.get("/{equipment_id}/status", response_model=StatusOut, responses=NOT_FOUND,
            summary="Текущее состояние: статус, RUL, вероятность дефекта, невязка")
def get_status(equipment_id: int, db: DB):
    return _found(equipment_service.get_status(db, equipment_id), equipment_id)


@router.get("/{equipment_id}/history", response_model=list[ReadingOut], responses=NOT_FOUND,
            summary="История показаний датчиков за период")
def get_history(equipment_id: int, db: DB,
                from_cycle: int | None = Query(None, ge=0, description="С какого цикла (включительно)"),
                to_cycle: int | None = Query(None, ge=0, description="По какой цикл (включительно)"),
                limit: int = Query(500, ge=1, le=5000, description="Максимум записей (берутся последние)")):
    if from_cycle is not None and to_cycle is not None and from_cycle > to_cycle:
        raise HTTPException(status_code=400, detail="from_cycle не может быть больше to_cycle")
    return _found(equipment_service.get_history(db, equipment_id, from_cycle, to_cycle, limit), equipment_id)


@router.get("/{equipment_id}/physics", response_model=list[PhysicsPointOut], responses=NOT_FOUND,
            summary="Физическая модель против фактических показаний: ожидаемая и фактическая деградация")
def get_physics(equipment_id: int, db: DB,
                limit: int = Query(500, ge=1, le=5000, description="Максимум записей (берутся последние)")):
    return _found(equipment_service.get_physics(db, equipment_id, limit), equipment_id)


@router.get("/{equipment_id}/forecast", response_model=ForecastOut, responses=NOT_FOUND,
            summary="Прогноз деградации: RUL по будущим циклам с доверительным интервалом")
def get_forecast(equipment_id: int, db: DB):
    return _found(equipment_service.get_forecast(db, equipment_id), equipment_id)
