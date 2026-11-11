from app.api import alerts, auth, equipment, predict
from app.api.auth import UNAUTHORIZED, get_current_user
from app.core.config import CORS_ORIGINS
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OFF-Tech: оценка состояния оборудования", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

# Данные — только с токеном; /auth/register и /auth/login открыты.
PROTECTED = [Depends(get_current_user)]

app.include_router(auth.router)
app.include_router(equipment.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
app.include_router(alerts.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
app.include_router(predict.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
