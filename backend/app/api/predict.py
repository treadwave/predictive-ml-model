from fastapi import APIRouter

from app.core.db import DB
from app.core.errors import MODEL_UNAVAILABLE, NOT_FOUND, equipment_not_found
from app.schemas.equipment import StatusOut
from app.schemas.predict import PredictIn
from app.services import predict_service

router = APIRouter(prefix="/predict", tags=["Прогнозирование"])


@router.post("", response_model=StatusOut, responses={**NOT_FOUND, **MODEL_UNAVAILABLE},
             summary="Ручной запрос инференса")
def predict(body: PredictIn, db: DB):
    result = predict_service.run_prediction(db, body.equipment_id)
    if result is None:
        raise equipment_not_found(body.equipment_id)
    return result
