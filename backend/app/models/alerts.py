from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)

from app.core.db import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(BigInteger, primary_key=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)
    ml_prediction_id = Column(BigInteger, ForeignKey("ml_predictions.id"), nullable=True)
    cycle = Column(Integer, nullable=False)
    triggered_at = Column(DateTime, nullable = False, server_default=func.now())
    severity = Column(Text, nullable=False)
    message = Column(Text, nullable=False)

    __table_args__ = (Index("ix_alerts_equipment_triggered", equipment_id, triggered_at.desc()),)

