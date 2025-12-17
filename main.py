from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Annotated
from datetime import datetime
import uvicorn

from database import get_db, init_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from models import (
    Work, Activity, ActivityDependency,
    WorkCreate, WorkUpdate, WorkResponse, WorkSummary,
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivitySummary,
    DependencyCreate, DependencyResponse,
    ActivityStatus, ActivityPriority, WorkType,
    VALID_TRANSITIONS
)
# from api_sprint1 import create_programacao_endpoints  # Desativado temporariamente
from app.routers import auth
from api_sprint0 import router as sprint0_router

app = FastAPI(
    title="OBRAX QUANTUM API",
    description="Sistema de Gestão de Obras - ERP Nativo",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar banco na startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Criar endpoints do Sprint 0
app.include_router(sprint0_router, prefix="/api/sprint0", tags=["Sprint 0"])

# Criar endpoints do Sprint 1 (DESATIVADO - aguardando migração para models.py)
# create_programacao_endpoints(app)
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# ==================== ROOT ====================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "OBRAX QUANTUM API",
        "message": "Backend online",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== HEALTH ====================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "OBRAX QUANTUM API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== DB TEST ====================

@app.get("/db-test")
async def db_test(db: Session = Depends(get_db)):
    """
    Testa a conexão REAL com o banco de dados.
    Se retornar {"db": "ok", "result": 1}, a conexão está funcionando.
    """
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {"db": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

# ==================== OBRAS ====================

@app.get("/api/works", response_model=List[WorkResponse])
async def get_works(
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    work_type: Optional[WorkType] = None,
    db: Session = Depends(get_db)
):
    """Listar todas as obras com filtros opcionais"""
    query = db.query(Work)

    if status:
        query = query.filter(Work.status == status)
    if work_type:
        query = query.filter(Work.work_type == work_type)

    works = query.offset(skip).limit(limit).all()
    return works

@app.get("/api/works/summary", response_model=List[WorkSummary])
async def get_works_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Obter resumo de todas as obras com estatísticas"""
    works = db.query(Work).all()
    summaries = []

    for work in works:
        activities = db.query(Activity).filter(Activity.work_id == work.id).all()
        total_activities = len(activities)
        completed_activities = len([a for a in activities if a.status == ActivityStatus.CLOSED])

        progress = (completed_activities / total_activities * 100) if total_activities > 0 else 0

        summaries.append(WorkSummary(
            id=work.id,
            name=work.name,
            work_type=work.work_type,
            status=work.status,
            total_activities=total_activities,
            completed_activities=completed_activities,
            progress_percentage=round(progress, 2),
            start_date=work.start_date,
            end_date=work.end_date,
            budget=work.budget
        ))

    return summaries

@app.get("/api/works/{work_id}", response_model=WorkResponse)
async def get_work(
    work_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Obter detalhes de uma obra específica"""
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Obra não encontrada")
    return work

@app.post("/api/works", response_model=WorkResponse)
async def create_work(
    work: WorkCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Criar nova obra"""
    db_work = Work(**work.dict())
    db.add(db_work)
    db.commit()
    db.refresh(db_work)
    return db_work

@app.put("/api/works/{work_id}", response_model=WorkResponse)
async def update_work(
    work_id: int,
    work_update: WorkUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Atualizar obra existente"""
    db_work = db.query(Work).filter(Work.id == work_id).first()
    if not db_work:
        raise HTTPException(status_code=404, detail="Obra não encontrada")

    update_data = work_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_work, field, value)

    db_work.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_work)
    return db_work

@app.delete("/api/works/{work_id}")
async def delete_work(
    work_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Excluir obra"""
    db_work = db.query(Work).filter(Work.id == work_id).first()
    if not db_work:
        raise HTTPException(status_code=404, detail="Obra não encontrada")

    db.delete(db_work)
    db.commit()
    return {"message": "Obra excluída com sucesso"}

# ==================== ATIVIDADES ====================

@app.get("/api/activities", response_model=List[ActivityResponse])
async def get_activities(
    current_user: Annotated[User, Depends(get_current_active_user)],
    work_id: Optional[int] = None,
    status: Optional[ActivityStatus] = None,
    discipline: Optional[str] = None,
    responsible_user: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Listar atividades com filtros"""
    query = db.query(Activity)

    if work_id:
        query = query.filter(Activity.work_id == work_id)
    if status:
        query = query.filter(Activity.status == status)
    if discipline:
        query = query.filter(Activity.discipline.ilike(f"%{discipline}%"))
    if responsible_user:
        query = query.filter(Activity.responsible_user.ilike(f"%{responsible_user}%"))

    activities = query.offset(skip).limit(limit).all()
    return activities

@app.get("/api/activities/summary", response_model=List[ActivitySummary])
async def get_activities_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    work_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Obter resumo das atividades com informações de atraso"""
    query = db.query(Activity)
    if work_id:
        query = query.filter(Activity.work_id == work_id)

    activities = query.all()
    summaries = []

    for activity in activities:
        days_overdue = None
        if activity.planned_end and activity.status not in [ActivityStatus.CLOSED]:
            days_overdue = (datetime.utcnow() - activity.planned_end).days
            days_overdue = max(0, days_overdue)

        summaries.append(ActivitySummary(
            id=activity.id,
            name=activity.name,
            ifs_code=activity.ifs_code,
            discipline=activity.discipline,
            status=activity.status,
            priority=activity.priority,
            progress_percentage=activity.progress_percentage,
            responsible_user=activity.responsible_user,
            planned_start=activity.planned_start,
            planned_end=activity.planned_end,
            days_overdue=days_overdue
        ))

    return summaries

@app.get("/api/activities/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Obter detalhes de uma atividade específica"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")
    return activity

@app.post("/api/activities", response_model=ActivityResponse)
async def create_activity(
    activity: ActivityCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Criar nova atividade"""
    work = db.query(Work).filter(Work.id == activity.work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Obra não encontrada")

    db_activity = Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity

@app.put("/api/activities/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: int,
    activity_update: ActivityUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Atualizar atividade existente"""
    db_activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not db_activity:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    update_data = activity_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_activity, field, value)

    db_activity.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_activity)
    return db_activity

@app.post("/api/activities/{activity_id}/change-status")
async def change_activity_status(
    current_user: Annotated[User, Depends(get_current_active_user)],
    activity_id: int,
    new_status: ActivityStatus,
    db: Session = Depends(get_db)
):
    """Alterar status de uma atividade (com validação da máquina de estados)"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    current_status = activity.status

    if new_status not in VALID_TRANSITIONS.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Transição inválida: {current_status} -> {new_status}"
        )

    activity.status = new_status
    activity.updated_at = datetime.utcnow()

    if new_status == ActivityStatus.IN_EXECUTION and not activity.actual_start:
        activity.actual_start = datetime.utcnow()
    elif new_status == ActivityStatus.CLOSED and not activity.actual_end:
        activity.actual_end = datetime.utcnow()
        activity.progress_percentage = 100.0

    db.commit()
    db.refresh(activity)

    return {
        "message": f"Status alterado de {current_status} para {new_status}",
        "activity": activity
    }

@app.get("/api/activities/{activity_id}/valid-transitions")
async def get_valid_transitions(
    activity_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """Obter transições válidas para uma atividade"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Atividade não encontrada")

    valid_transitions = VALID_TRANSITIONS.get(activity.status, [])
    return {
        "current_status": activity.status,
        "valid_transitions": valid_transitions
    }

# ==================== DASHBOARD ====================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    work_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Obter estatísticas para o dashboard"""
    works_query = db.query(Work)
    activities_query = db.query(Activity)

    if work_id:
        works_query = works_query.filter(Work.id == work_id)
        activities_query = activities_query.filter(Activity.work_id == work_id)

    works = works_query.all()
    activities = activities_query.all()

    total_works = len(works)
    total_activities = len(activities)

    status_counts = {}
    for status_item in ActivityStatus:
        status_counts[status_item.value] = len([a for a in activities if a.status == status_item])

    overdue_activities = []
    for activity in activities:
        if (
            activity.planned_end and
            activity.status not in [ActivityStatus.CLOSED] and
            datetime.utcnow() > activity.planned_end
        ):
            overdue_activities.append(activity)

    total_progress = sum(a.progress_percentage for a in activities)
    avg_progress = (total_progress / total_activities) if total_activities > 0 else 0

    return {
        "total_works": total_works,
        "total_activities": total_activities,
        "status_distribution": status_counts,
        "overdue_activities": len(overdue_activities),
        "average_progress": round(avg_progress, 2),
        "activities_by_priority": {
            "HIGH": len([a for a in activities if a.priority == ActivityPriority.HIGH]),
            "MEDIUM": len([a for a in activities if a.priority == ActivityPriority.MEDIUM]),
            "LOW": len([a for a in activities if a.priority == ActivityPriority.LOW]),
            "CRITICAL": len([a for a in activities if a.priority == ActivityPriority.CRITICAL]),
        }
    }

@app.get("/api/test", dependencies=[Depends(get_current_active_user)])
async def test_endpoint():
    return {
        "status": "success",
        "message": "API funcionando corretamente",
        "features": [
            "Gestão de Obras",
            "Controle de Atividades",
            "Máquina de Estados",
            "Dashboard em Tempo Real"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
