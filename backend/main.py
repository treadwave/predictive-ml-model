from app.api import alerts, auth, equipment, health, predict, sensors, users
from app.api.auth import UNAUTHORIZED, get_current_user
from app.core.config import CORS_ORIGINS
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title="OFF-Tech: оценка состояния оборудования", version="0.1.0")

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

# Данные — только с токеном; публичный вход только через /auth/login.
PROTECTED = [Depends(get_current_user)]

app.include_router(auth.router)
app.include_router(equipment.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
app.include_router(alerts.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
app.include_router(predict.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
app.include_router(sensors.router, dependencies=PROTECTED, responses=UNAUTHORIZED)
# Проверка живости — без токена, чтобы её могли дёргать healthcheck и мониторинг.
app.include_router(health.router)

app.include_router(users.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    # Default validation responses echo submitted values, including passwords.
    errors = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})
