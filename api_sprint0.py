"""
OBRAX QUANTUM - Sprint 0
Endpoints para PCC, FVS, NC e Painel do Encarregado
"""

import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Activity, ActivityStatus,
    EventPCC, EventPCCCreate, EventPCCResponse,
    EventFVS, EventFVSCreate, EventFVSResponse,
    EventNC, EventNCResponse,
    FVSStatus, NCOrigin, NCStatus,
    VALID_TRANSITIONS
)

# ⚠️ import do User só para DEV seed
from app.models.user import User
from app.routers.auth import get_password_hash

router = APIRouter()

# =========================================================
# HELPERS
# =========================================================

def validate_state_transition(current_status: ActivityStatus, target_status: ActivityStatus) -> bool:
    allowed_transitions = VALID_TRANSITIONS.get(current_status, [])
    return target_status in allowed_transitions


def get_next_status_after_pcc(current_status: ActivityStatus) -> ActivityStatus:
    if current_status != ActivityStatus.PCC_REQUIRED:
        raise ValueError(f"Cannot confirm PCC from state: {current_status}")
    return ActivityStatus.PCC_CONFIRMED


def get_next_status_after_fvs(current_status: ActivityStatus, fvs_result: FVSStatus) -> ActivityStatus:
    if current_status != ActivityStatus.INSPECTION_PENDING:
        raise ValueError(f"Cannot inspect FVS from state: {current_status}")
    return (
        ActivityStatus.INSPECTED_PASS
        if fvs_result == FVSStatus.PASS
        else ActivityStatus.INSPECTED_FAIL
    )

# =========================================================
# HEALTH
# =========================================================

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "OBRAX QUANTUM API - Sprint 0"
    }

# =========================================================
# PCC
# =========================================================

@router.post("/pcc/confirm", response_model=dict)
async def confirm_pcc(event: EventPCCCreate, db: Session = Depends(get_db)):
    task = db.query(Activity).filter(Activity.id == event.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != ActivityStatus.PCC_REQUIRED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm PCC from state: {task.status}"
        )

    pcc_event = EventPCC(
        obra_id=event.obra_id,
        atividade_id=event.atividade_id,
        equipe_id=event.equipe_id,
        task_id=event.task_id,
        requested_at=datetime.utcnow(),
        confirmed_at=datetime.utcnow(),
        confirmed_flag=1,
        executor_id=1
    )
    db.add(pcc_event)

    task.status = get_next_status_after_pcc(task.status)
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
    return (
        db.query(EventPCC)
        .filter(EventPCC.obra_id == obra_id)
        .order_by(EventPCC.created_at.desc())
        .all()
    )

# =========================================================
# FVS
# =========================================================

@router.post("/fvs/inspect", response_model=dict)
async def inspect_fvs(event: EventFVSCreate, db: Session = Depends(get_db)):
    task = db.query(Activity).filter(Activity.id == event.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != ActivityStatus.INSPECTION_PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot inspect FVS from state: {task.status}"
        )

    fvs_event = EventFVS(
        obra_id=event.obra_id,
        service_id=event.service_id,
        task_id=event.task_id,
        executor_id=1,
        inspected_at=datetime.utcnow(),
        status=event.status,
        rework_count=0,
        observations=event.observations
    )
    db.add(fvs_event)
    db.flush()

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

    task.status = get_next_status_after_fvs(task.status, event.status)
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
    return (
        db.query(EventFVS)
        .filter(EventFVS.obra_id == obra_id)
        .order_by(EventFVS.created_at.desc())
        .all()
    )

# =========================================================
# NC
# =========================================================

@router.get("/nc/list/{obra_id}", response_model=List[EventNCResponse])
async def list_nc_events(obra_id: int, db: Session = Depends(get_db)):
    return (
        db.query(EventNC)
        .filter(EventNC.obra_id == obra_id)
        .order_by(EventNC.created_at.desc())
        .all()
    )

# =========================================================
# TASKS / PAINEL ENCARREGADO
# =========================================================

@router.get("/tasks/list/{obra_id}")
async def list_tasks(
    obra_id: int,
    encarregado: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Lista atividades da obra.
    - Se encarregado for informado, filtra por Activity.responsible_user
    """
    q = db.query(Activity).filter(Activity.work_id == obra_id)

    if encarregado:
        q = q.filter(Activity.responsible_user == encarregado)

    return q.order_by(Activity.created_at.desc()).all()

# =========================================================
# DEV SEED - ATIVIDADES
# =========================================================

@router.post("/dev/seed")
async def dev_seed(obra_id: int, db: Session = Depends(get_db)):
    if os.getenv("ENABLE_DEV_SEED", "").lower() not in ("1", "true", "yes", "on"):
        raise HTTPException(status_code=404, detail="Not found")

    already = db.query(Activity).filter(Activity.work_id == obra_id).first()
    if already:
        return {"ok": True, "created": 0, "message": "Seed skipped (already exists)"}

    now = datetime.utcnow()
    demo = [
        Activity(
            work_id=obra_id,
            name="Instalar contramarco",
            status=ActivityStatus.PCC_REQUIRED,
            responsible_user="Marcelo",
            created_at=now,
            updated_at=now
        ),
        Activity(
            work_id=obra_id,
            name="Aplicar manta acústica",
            status=ActivityStatus.READY,
            responsible_user="Nicolas",
            created_at=now,
            updated_at=now
        ),
        Activity(
            work_id=obra_id,
            name="FVS Porta corta-fogo",
            status=ActivityStatus.INSPECTION_PENDING,
            responsible_user="Marcelo",
            created_at=now,
            updated_at=now
        ),
    ]

    db.add_all(demo)
    db.commit()
    return {"ok": True, "created": len(demo), "obra_id": obra_id}

# =========================================================
# DEV SEED - USUÁRIOS
# =========================================================

@router.post("/dev/seed_users")
async def dev_seed_users(db: Session = Depends(get_db)):
    if os.getenv("ENABLE_DEV_SEED", "").lower() not in ("1", "true", "yes", "on"):
        raise HTTPException(status_code=404, detail="Not found")

    users = [
        ("marcelo", "123456"),
        ("nicolas", "123456"),
        ("mestre", "123456"),
    ]

    created = 0
    for username, pwd in users:
        exists = db.query(User).filter(User.username == username).first()
        if not exists:
            db.add(
                User(
                    username=username,
                    hashed_password=get_password_hash(pwd),
                    is_active=True
                )
            )
            created += 1

    db.commit()
    return {"ok": True, "created": created}
