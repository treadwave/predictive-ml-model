from app.api import alerts, equipment, health, predict, sensors
from app.core.config import CORS_ORIGINS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OFF-Tech: оценка состояния оборудования", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(equipment.router)
app.include_router(alerts.router)
app.include_router(predict.router)
app.include_router(sensors.router)
app.include_router(health.router)
