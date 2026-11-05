from sqlalchemy import Connection, select

from app.models.sensor_catalog import SensorCatalog


def list_sensors(db: Connection) -> list[dict]:
    rows = [dict(row) for row in db.execute(select(SensorCatalog)).mappings()]
    return sorted(rows, key=lambda row: int(row["code"][1:]))
