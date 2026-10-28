from sqlalchemy import Boolean, Column, Text

from app.core.db import Base


class SensorCatalog(Base):
    __tablename__ = "sensor_catalog"

    code = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    unit = Column(Text, nullable=True)
    is_used = Column(Boolean, nullable=False)
