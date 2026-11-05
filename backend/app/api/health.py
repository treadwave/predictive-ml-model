from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import engine

router = APIRouter(prefix="/health", tags=["Служебное"])


@router.get("", summary="Проверка работоспособности")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="База данных недоступна") from exc
    return {"status": "ok"}
