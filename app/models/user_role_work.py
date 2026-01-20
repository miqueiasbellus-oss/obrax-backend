
# app/models/user_role_work.py
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from datetime import datetime

from models import Base


class UserRoleWork(Base):
    """
    Liga: User + Role + Work (Obra)
    Ex:
      - Marcelo tem Role=ENCARREGADO na Obra 1
      - Nicolas tem Role=ENCARREGADO na Obra 1
      - Você tem Role=MASTER na Obra 1
    """
    __tablename__ = "user_role_work"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "work_id", name="uq_user_role_work"),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, index=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
