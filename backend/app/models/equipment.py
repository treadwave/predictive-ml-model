from sqlalchemy import UniqueConstraint
from app.core.db import Base
from sqlalchemy import Column, Integer, Date, Text

class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    dataset = Column(Text, nullable=False)
    unit_number = Column(Integer, nullable=False)
    install_date = Column(Date, nullable=False)
    last_maintenance_date = Column(Date, nullable=True)

    __table_args__ = (UniqueConstraint("dataset", "unit_number"),)
