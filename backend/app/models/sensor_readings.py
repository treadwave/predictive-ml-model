from sqlalchemy import UniqueConstraint, BigInteger, ForeignKey
from app.core.db import Base
from sqlalchemy import Column, Integer, DateTime, REAL, func

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(BigInteger, primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable = False)
    cycle = Column(Integer, nullable = False)
    s2 = Column(REAL)
    s3 = Column(REAL)
    s4 = Column(REAL)
    s7 = Column(REAL)
    s8 = Column(REAL)
    s9 = Column(REAL)
    s11 = Column(REAL)
    s12 = Column(REAL)
    s13 = Column(REAL)
    s14 = Column(REAL)
    s15 = Column(REAL)
    s17 = Column(REAL)
    s20 = Column(REAL)
    s21 = Column(REAL)
    rul = Column(Integer, nullable = True)
    created_at = Column(DateTime, nullable = False, server_default=func.now())

    __table_args__ = (UniqueConstraint("equipment_id", "cycle"), )


