import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base  # Base principal do projeto

# URL do banco (Render ou SQLite local)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./obrax_quantum.db")

# Render às vezes usa postgres:// (antigo)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Cria uma sessão por request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa o banco:
    - importa TODOS os modelos
    - cria tabelas
    """
    try:
        print("Inicializando banco de dados...")

        # IMPORTA TODOS OS MODELOS QUE USAM Base
        from models import Work, Activity, ActivityDependency
        from app.models.user import User  # <-- IMPORTANTE

        Base.metadata.create_all(bind=engine)

        print("Banco de dados inicializado com sucesso (sem dados de exemplo).")
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")


if __name__ == "__main__":
    init_db()
