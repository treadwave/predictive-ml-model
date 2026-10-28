from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)

from app.core.db import Base


class MlPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(BigInteger, primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    cycle = Column(Integer, nullable=False)
    predicted_rul = Column(Float, nullable=False)
    defect_probability = Column(Float, nullable=False)
    residual = Column(Float, nullable=False)
    model_version = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("equipment_id", "cycle"), )
