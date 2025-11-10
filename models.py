from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Enums para Estados das Atividades (baseado no PO11)
class ActivityStatus(str, Enum):
    PLANNED = "PLANNED"
    PCC_REQUIRED = "PCC_REQUIRED"
    PCC_CONFIRMED = "PCC_CONFIRMED"
    READY = "READY"
    IN_EXECUTION = "IN_EXECUTION"
    INSPECTION_PENDING = "INSPECTION_PENDING"
    INSPECTED_PASS = "INSPECTED_PASS"
    INSPECTED_FAIL = "INSPECTED_FAIL"
    PARTIAL_CLOSED = "PARTIAL_CLOSED"
    CLOSED = "CLOSED"
    REWORK = "REWORK"
    BLOCKED = "BLOCKED"

class ActivityPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class WorkType(str, Enum):
    CONSTRUCTION = "CONSTRUCTION"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    RENOVATION = "RENOVATION"
    MAINTENANCE = "MAINTENANCE"

# Modelos SQLAlchemy (Banco de Dados)
class Work(Base):
    __tablename__ = "works"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    work_type = Column(SQLEnum(WorkType), default=WorkType.CONSTRUCTION)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    budget = Column(Float)
    client_name = Column(String(255))
    location = Column(String(500))
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    activities = relationship("Activity", back_populates="work", cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Estrutura IFS (Identificação, Frente, Serviço)
    ifs_code = Column(String(50), index=True)  # Ex: PE01201_FS01403
    discipline = Column(String(100))  # Ex: "Alvenaria"
    front = Column(String(100))      # Ex: "Pavimento Térreo"
    service_type = Column(String(100)) # Ex: "Alvenaria de Vedação"
    
    # Estados e Controle
    status = Column(SQLEnum(ActivityStatus), default=ActivityStatus.PLANNED)
    priority = Column(SQLEnum(ActivityPriority), default=ActivityPriority.MEDIUM)
    progress_percentage = Column(Float, default=0.0)
    
    # Datas
    planned_start = Column(DateTime)
    planned_end = Column(DateTime)
    actual_start = Column(DateTime)
    actual_end = Column(DateTime)
    
    # Recursos
    estimated_hours = Column(Float)
    actual_hours = Column(Float)
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    
    # Responsáveis
    responsible_user = Column(String(255))
    team_members = Column(JSON)  # Lista de membros da equipe
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    work = relationship("Work", back_populates="activities")
    dependencies = relationship("ActivityDependency", foreign_keys="ActivityDependency.activity_id", back_populates="activity")
    dependents = relationship("ActivityDependency", foreign_keys="ActivityDependency.depends_on_id", back_populates="depends_on")

class ActivityDependency(Base):
    __tablename__ = "activity_dependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    depends_on_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    dependency_type = Column(String(50), default="FINISH_TO_START")  # FS, SS, FF, SF
    lag_days = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    activity = relationship("Activity", foreign_keys=[activity_id], back_populates="dependencies")
    depends_on = relationship("Activity", foreign_keys=[depends_on_id], back_populates="dependents")

# Modelos Pydantic (API)
class WorkBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    work_type: WorkType = WorkType.CONSTRUCTION
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    client_name: Optional[str] = None
    location: Optional[str] = None

class WorkCreate(WorkBase):
    pass

class WorkUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    work_type: Optional[WorkType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    client_name: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None

class WorkResponse(WorkBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ActivityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    ifs_code: Optional[str] = None
    discipline: Optional[str] = None
    front: Optional[str] = None
    service_type: Optional[str] = None
    priority: ActivityPriority = ActivityPriority.MEDIUM
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    responsible_user: Optional[str] = None
    team_members: Optional[List[str]] = None

class ActivityCreate(ActivityBase):
    work_id: int

class ActivityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ifs_code: Optional[str] = None
    discipline: Optional[str] = None
    front: Optional[str] = None
    service_type: Optional[str] = None
    status: Optional[ActivityStatus] = None
    priority: Optional[ActivityPriority] = None
    progress_percentage: Optional[float] = Field(None, ge=0, le=100)
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    responsible_user: Optional[str] = None
    team_members: Optional[List[str]] = None

class ActivityResponse(ActivityBase):
    id: int
    work_id: int
    status: ActivityStatus
    progress_percentage: float
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    actual_hours: Optional[float] = None
    actual_cost: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class DependencyCreate(BaseModel):
    activity_id: int
    depends_on_id: int
    dependency_type: str = "FINISH_TO_START"
    lag_days: int = 0

class DependencyResponse(BaseModel):
    id: int
    activity_id: int
    depends_on_id: int
    dependency_type: str
    lag_days: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Modelos para Dashboard
class WorkSummary(BaseModel):
    id: int
    name: str
    work_type: WorkType
    status: str
    total_activities: int
    completed_activities: int
    progress_percentage: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None

class ActivitySummary(BaseModel):
    id: int
    name: str
    ifs_code: Optional[str] = None
    discipline: Optional[str] = None
    status: ActivityStatus
    priority: ActivityPriority
    progress_percentage: float
    responsible_user: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    days_overdue: Optional[int] = None

# Modelo para Estados Válidos (Máquina de Estados)
class StatusTransition(BaseModel):
    from_status: ActivityStatus
    to_status: ActivityStatus
    conditions: Optional[Dict[str, Any]] = None
    required_fields: Optional[List[str]] = None

# Definição das transições válidas da máquina de estados
VALID_TRANSITIONS = {
    ActivityStatus.PLANNED: [ActivityStatus.PCC_REQUIRED, ActivityStatus.READY, ActivityStatus.BLOCKED],
    ActivityStatus.PCC_REQUIRED: [ActivityStatus.PCC_CONFIRMED, ActivityStatus.BLOCKED],
    ActivityStatus.PCC_CONFIRMED: [ActivityStatus.READY, ActivityStatus.BLOCKED],
    ActivityStatus.READY: [ActivityStatus.IN_EXECUTION, ActivityStatus.BLOCKED],
    ActivityStatus.IN_EXECUTION: [ActivityStatus.INSPECTION_PENDING, ActivityStatus.PARTIAL_CLOSED, ActivityStatus.BLOCKED],
    ActivityStatus.INSPECTION_PENDING: [ActivityStatus.INSPECTED_PASS, ActivityStatus.INSPECTED_FAIL],
    ActivityStatus.INSPECTED_PASS: [ActivityStatus.CLOSED, ActivityStatus.PARTIAL_CLOSED],
    ActivityStatus.INSPECTED_FAIL: [ActivityStatus.REWORK],
    ActivityStatus.REWORK: [ActivityStatus.IN_EXECUTION, ActivityStatus.BLOCKED],
    ActivityStatus.PARTIAL_CLOSED: [ActivityStatus.CLOSED, ActivityStatus.IN_EXECUTION],
    ActivityStatus.BLOCKED: [ActivityStatus.PLANNED, ActivityStatus.PCC_REQUIRED, ActivityStatus.READY],
    ActivityStatus.CLOSED: []  # Estado final
}

