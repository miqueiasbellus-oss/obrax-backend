import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./obrax_quantum.db")

# Ajuste automático caso o prefixo venha como "postgres://"
raw_db_url = DATABASE_URL
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = raw_db_url

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Criar todas as tabelas no banco de dados"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency para obter sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializa o banco de dados:
    - Cria as tabelas com base no Base.metadata
    (não insere usuário inicial nem dados de exemplo por enquanto)
    """
    try:
        print("Inicializando banco de dados...")
        create_tables()
        print("Banco de dados inicializado com sucesso (sem dados de exemplo).")
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")


if __name__ == "__main__":
    init_db()
