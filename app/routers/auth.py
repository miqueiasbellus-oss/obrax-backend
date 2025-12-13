from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from app.models.user import User

# Usamos apenas a criação de token do core
from app.core.security import create_access_token

# Nossa própria configuração de hash de senha
from passlib.context import CryptContext

# pbkdf2_sha256 não tem limite de 72 bytes como o bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ---------- Funções de senha ----------

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------- Função de autenticação comum ----------

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------- Schemas Pydantic ----------

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- /auth/register ----------

@router.post("/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Cria um novo usuário.
    POST /auth/register
    Body JSON: {"username": "...", "password": "..."}
    """
    try:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed = get_password_hash(payload.password)

        user = User(
            username=payload.username,
            hashed_password=hashed,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return {"message": "User created successfully", "username": user.username}

    except HTTPException:
        # Se for erro de validação nosso (ex: username já existe), só repassa
        raise
    except Exception as e:
        # Aqui captura QUALQUER erro e devolve o nome/descrição no detail
        raise HTTPException(
            status_code=500,
            detail=f"Register error: {type(e).__name__}: {e}"
        )


# ---------- /auth/login (JSON) ----------

@router.post("/login")
def login_json(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Login via JSON.
    POST /auth/login
    Body JSON: {"username": "...", "password": "..."}
    """
    try:
        user = authenticate_user(db, payload.username, payload.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )

        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login error: {type(e).__name__}: {e}"
        )


# ---------- /auth/token (OAuth2 form-data) ----------

@router.post("/token")
def login_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """
    Login no padrão OAuth2PasswordRequestForm.
    POST /auth/token
    Body form-data: username, password
    """
    try:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )

        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token error: {type(e).__name__}: {e}"
        )
