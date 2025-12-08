from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.security import create_access_token, verify_password
from database import get_db
from app.models.user import User

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 30


# --------- Função utilitária de autenticação ---------
def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Retorna o usuário se usuário+senha estiverem corretos, senão None.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


# --------- Endpoint padrão OAuth2 (form-data) ---------
@router.post("/token", response_model=dict)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """
    Endpoint no padrão OAuth2PasswordRequestForm.
    Usa form-data: username, password, grant_type, etc.
    Caminho final: POST /auth/token
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# --------- Endpoint JSON "normal" para o frontend ---------
class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login", response_model=dict)
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint de login via JSON:
    POST /auth/login
    Body:
    {
      "username": "seu_usuario",
      "password": "sua_senha"
    }
    """
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Mesmo formato do /auth/token
    return {"access_token": access_token, "token_type": "bearer"}
