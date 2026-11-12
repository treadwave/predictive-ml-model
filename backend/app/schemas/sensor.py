from pydantic import BaseModel, Field


class SensorOut(BaseModel):
    code: str
    name: str
    unit: str | None = Field(description="Единица измерения")
    is_used: bool = Field(description="Участвует ли датчик в модели")
