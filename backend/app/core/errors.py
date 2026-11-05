from fastapi import HTTPException


def equipment_not_found(equipment_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Оборудование с id={equipment_id} не найдено")


def model_unavailable() -> HTTPException:
    return HTTPException(status_code=503, detail="Модель прогноза недоступна")


NOT_FOUND = {404: {"description": "Оборудование не найдено"}}
MODEL_UNAVAILABLE = {503: {"description": "Модель прогноза недоступна"}}
