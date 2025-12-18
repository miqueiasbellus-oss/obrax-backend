"""
OBRAX QUANTUM - Sprint 0
Endpoints para PCC, FVS e NC
"""

import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
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

router = APIRouter()

# ==================== HELPER FUNCTIONS ====================

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
    return ActivityStatus.INSPECTED_PASS if fvs_result == FVSStatus.PASS else ActivityStatus.INSPECTED_FAIL

# ==================== HEALTH ENDPOINT ====================

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "OBRAX QUANTUM API - Sprint 0"
    }

# ==================== PCC ENDPOINTS ====================

@router.post("/pcc/confirm", response_model=dict)
async def confirm_pcc(event: EventPCCCreate, db: Session = Depends(get_db)):
    task = db.query(Activity).filter(Activity.id == event.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != ActivityStatus.PCC_REQUIRED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm PCC from state: {task.status}. Task must be in PCC_REQUIRED state."
        )

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
    return (
        db.query(EventPCC)
        .filter(EventPCC.obra_id == obra_id)
        .order_by(EventPCC.created_at.desc())
        .all()
    )

# ==================== FVS ENDPOINTS ====================

@router.post("/fvs/inspect", response_model=dict)
async def inspect_fvs(event: EventFVSCreate, db: Session = Depends(get_db)):
    task = db.query(Activity).filter(Activity.id == event.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != ActivityStatus.INSPECTION_PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot inspect FVS from state: {task.status}. Task must be in INSPECTION_PENDING state."
        )

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
    db.flush()  # pega fvs_event.id antes do commit

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
    return (
        db.query(EventFVS)
