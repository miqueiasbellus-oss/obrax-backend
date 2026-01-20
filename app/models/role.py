# app/models/role.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from models import Base  # usa o Base principal do projeto


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)   # ex: "MASTER", "ENCARREGADO"
    name = Column(String, nullable=False)                           # ex: "Master", "Encarregado"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

