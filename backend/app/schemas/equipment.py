from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["normal", "warning", "critical"]


class EquipmentOut(BaseModel):
    id: int
    name: str
    type: str
    unit_number: int
    last_maintenance_date: date | None = Field(None, description="Дата последнего обслуживания")
    current_cycle: int
    status: Status
    predicted_rul: float = Field(description="Прогноз остаточного ресурса, циклов")


class StatusOut(BaseModel):
    equipment_id: int
    status: Status = Field(description="normal: RUL > 75, warning: 31–75, critical: ≤ 30 циклов")
    current_cycle: int
    predicted_rul: float = Field(description="Прогноз остаточного ресурса, циклов")
    defect_probability: float = Field(ge=0, le=1, description="Вероятность дефекта, 0–1")
    residual: float = Field(description="Невязка: отклонение от физически ожидаемого поведения")


class ReadingOut(BaseModel):
    cycle: int
    sensors: dict[str, float] = Field(description="Показания 14 рабочих датчиков: код → значение")


class PhysicsPointOut(BaseModel):
    cycle: int
    expected: float = Field(description="Ожидаемая деградация по физической модели: 0 — исправный двигатель, 1 — отказ")
    actual: float = Field(description="Фактическая деградация по показаниям датчиков")
    residual: float = Field(description="Невязка: фактическая деградация минус ожидаемая")


class ForecastPoint(BaseModel):
    cycle: int
    rul: float = Field(description="Ожидаемый остаточный ресурс на этом цикле")
    rul_low: float = Field(description="Нижняя граница доверительного интервала")
    rul_high: float = Field(description="Верхняя граница доверительного интервала")


class ForecastOut(BaseModel):
    equipment_id: int
    current_cycle: int
    predicted_rul: float
    predicted_failure_cycle: int = Field(description="Цикл, на котором ожидается отказ")
    points: list[ForecastPoint] = Field(description="От текущего цикла до ожидаемого отказа, шаг — 1 цикл")
