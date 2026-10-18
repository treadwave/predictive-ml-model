from sqlalchemy import UniqueConstraint, BigInteger, ForeignKey
from app.core.db import Base
from sqlalchemy import Column, Integer, DateTime, func, Float

class PhysicsPrediction(Base):
    __tablename__ = "physics_predictions"

    id = Column(BigInteger, primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    cycle = Column(Integer, nullable=False)
    predicted_degradation = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("equipment_id", "cycle"),)
