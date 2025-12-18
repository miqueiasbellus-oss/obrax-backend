"""
OBRAX QUANTUM - Sprint 0
Endpoints para PCC, FVS e NC
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import (
    Activity, ActivityStatus,
    EventPCC, EventPCCCreate, EventPCCResponse,
    EventFVS, EventFVSCreate, EventFVSResponse,
    EventNC, EventNCResponse,
    FVSStatus, NCOrigin, NCStatus,
    VALID_TRANSITIONS
)

router = APIRouter()

# ==================== HELPER FUNCTIONS ====================

def validate_state_transition(current_status: ActivityStatus, target_status: ActivityStatus) -> bool:
    """Valida se a transição de estado é permitida"""
    allowed_transitions = VALID_TRANSITIONS.get(current_status, [])
    return target_status in allowed_transitions

def get_next_status_after_pcc(current_status: ActivityStatus) -> ActivityStatus:
    """Retorna o próximo estado após confirmação PCC"""
    if current_status != ActivityStatus.PCC_REQUIRED:
        raise ValueError(f"Cannot confirm PCC from state: {current_status}")
    return ActivityStatus.PCC_CONFIRMED

def get_next_status_after_fvs(current_status: ActivityStatus, fvs_result: FVSStatus) -> ActivityStatus:
    """Retorna o próximo estado após inspeção FVS"""
    if current_status != ActivityStatus.INSPECTION_PENDING:
        raise ValueError(f"Cannot inspect FVS from state: {current_status}")
    
    return ActivityStatus.INSPECTED_PASS if fvs_result == FVSStatus.PASS else ActivityStatus.INSPECTED_FAIL

# ==================== HEALTH ENDPOINT ====================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "OBRAX QUANTUM API - Sprint 0"
    }

# ==================== PCC ENDPOINTS ====================

@router.post("/pcc/confirm", response_model=dict)
async def confirm_pcc(
    event: EventPCCCreate,
    db: Session = Depends(get_db)
):
    """
    Confirma PCC (Planejamento e Controle de Conformidade)
    
    - Valida estado da tarefa
    - Cria evento PCC
    - Atualiza status da tarefa para PCC_CONFIRMED
    """
    # Get current task
    task = db.query(Activity).filter(Activity.id == event.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate state transition
    if task.status != ActivityStatus.PCC_REQUIRED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm PCC from state: {task.status}. Task must be in PCC_REQUIRED state."
        )
    
    # Create PCC event
    pcc_event = EventPCC(
        obra_id=event.obra_id,
        atividade_id=event.atividade_id,
        equipe_id=event.equipe_id,
        task_id=event.task_id,
        requested_at=datetime.utcnow(),
        confirmed_at=datetime.utcnow(),
        confirmed_flag=1,
        executor_id=1  # TODO: Get from auth context
    )
    db.add(pcc_event)
    
    # Update task status
    next_status = get_next_status_after_pcc(task.status)
    task.status = next_status
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(pcc_event)
    db.refresh(task)
    
    return {
        "success": True,
        "pcc_event": EventPCCResponse.model_validate(pcc_event),
        "new_status": task.status.value
    }

@router.get("/pcc/list/{obra_id}", response_model=List[EventPCCResponse])
async def list_pcc_events(obra_id: int, db: Session = Depends(get_db)):
    """Lista todos os eventos PCC de uma obra"""
    events = db.query(EventPCC).filter(EventPCC.obra_id == obra_id).order_by(EventPCC.created_at.desc()).all()
    return events

# ==================== FVS ENDPOINTS ====================

@router.post("/fvs/inspect", response_model=dict)
async def inspect_fvs(
    event: EventFVSCreate,
    db: Session = Depends(get_db)
):
    """
    Registra inspeção FVS (Fiscalização Visual de Serviço)
    
    - Valida estado da tarefa
    - Cria evento FVS
    - Se FAIL: cria NC automaticamente
    - Atualiza status da tarefa
    """
    # Get current task
    task = db.query(Activity).filter(Activity.id == event.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate state transition
    if task.status != ActivityStatus.INSPECTION_PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot inspect FVS from state: {task.status}. Task must be in INSPECTION_PENDING state."
        )
    
    # Create FVS event
    fvs_event = EventFVS(
        obra_id=event.obra_id,
        service_id=event.service_id,
        task_id=event.task_id,
        executor_id=1,  # TODO: Get from auth context
        inspected_at=datetime.utcnow(),
        status=event.status,
        rework_count=0,
        observations=event.observations
    )
    db.add(fvs_event)
    db.flush()  # Flush to get fvs_event.id
    
    # Create NC if FVS failed
    nc_event = None
    if event.status == FVSStatus.FAIL:
        nc_event = EventNC(
            obra_id=event.obra_id,
            service_id=event.service_id,
            task_id=event.task_id,
            fvs_id=fvs_event.id,
            origin=NCOrigin.FVS,
            status=NCStatus.ABERTA,
            description=f"NC automática criada por FVS FAIL. {event.observations or ''}"
        )
        db.add(nc_event)
    
    # Update task status
    next_status = get_next_status_after_fvs(task.status, event.status)
    task.status = next_status
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(fvs_event)
    if nc_event:
        db.refresh(nc_event)
    db.refresh(task)
    
    return {
        "success": True,
        "fvs_event": EventFVSResponse.model_validate(fvs_event),
        "nc_event": EventNCResponse.model_validate(nc_event) if nc_event else None,
        "new_status": task.status.value
    }

@router.get("/fvs/list/{obra_id}", response_model=List[EventFVSResponse])
async def list_fvs_events(obra_id: int, db: Session = Depends(get_db)):
    """Lista todos os eventos FVS de uma obra"""
    events = db.query(EventFVS).filter(EventFVS.obra_id == obra_id).order_by(EventFVS.created_at.desc()).all()
    return events

# ==================== NC ENDPOINTS ====================

@router.get("/nc/list/{obra_id}", response_model=List[EventNCResponse])
async def list_nc_events(obra_id: int, db: Session = Depends(get_db)):
    """Lista todos os eventos NC (Não Conformidade) de uma obra"""
    events = db.query(EventNC).filter(EventNC.obra_id == obra_id).order_by(EventNC.created_at.desc()).all()
    return events

# ==================== TASKS ENDPOINTS ====================

@router.get("/tasks/list/{obra_id}")
async def list_tasks(obra_id: int, db: Session = Depends(get_db)):
    """Lista todas as tarefas de uma obra"""
    tasks = db.query(Activity).filter(Activity.work_id == obra_id).order_by(Activity.created_at.desc()).all()
    return tasks

import os
from datetime import datetime

@router.post("/dev/seed")
async def dev_seed(obra_id: int, db: Session = Depends(get_db)):
    """
    DEV ONLY: cria tarefas demo na tabela Activity para uma obra.
    Só funciona se ENABLE_DEV_SEED=true.
    Idempotente: se já existir Activity para a obra, não duplica.
    """
    if os.getenv("ENABLE_DEV_SEED", "").lower() not in ("1", "true", "yes", "on"):
        raise HTTPException(status_code=404, detail="Not found")

    # Não duplica
    already = db.query(Activity).filter(Activity.work_id == obra_id).limit(1).all()
    if already:
        return {"ok": True, "created": 0, "message": "Seed skipped (activities already exist)"}

    now = datetime.utcnow()

    demo = [
        Activity(
            work_id=obra_id,
            name="Instalar contramarco (PCC)",
            status=ActivityStatus.PCC_REQUIRED,
            created_at=now,
            updated_at=now
        ),
        Activity(
            work_id=obra_id,
            name="Aplicar manta acústica (Execução)",
            status=ActivityStatus.READY,
            created_at=now,
            updated_at=now
        ),
        Activity(
            work_id=obra_id,
            name="FVS - Porta corta-fogo (Inspeção)",
            status=ActivityStatus.INSPECTION_PENDING,
            created_at=now,
            updated_at=now
        ),
    ]

    db.add_all(demo)
    db.commit()

    return {"ok": True, "created": len(demo), "obra_id": obra_id}
