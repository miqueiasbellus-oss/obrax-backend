import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./obrax_quantum.db")

# Para PostgreSQL em produção, use a variável de ambiente DATABASE_URL.
# Aqui fazemos um ajuste automático caso o prefixo venha como "postgres://"
raw_db_url = DATABASE_URL

# Corrige prefixo caso venha como postgres://
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
    """Inicializar banco de dados com dados de exemplo"""
    create_tables()
    
    # Importar aqui para evitar circular imports
    from models import Work, Activity, ActivityStatus, WorkType, ActivityPriority
    from models import User
    from auth import get_password_hash
    
    db = SessionLocal()
    try:
        # Verificar se já existe um usuário inicial
        if db.query(User).first():
            print("Usuário inicial já existe")
        else:
            print("Criando usuário inicial 'Miqueias'")
            hashed_password = get_password_hash("Miqueias$69")
            initial_user = User(
                username="Miqueias",
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(initial_user)
            db.commit()
            print("Usuário inicial criado com sucesso.")

        # Verificar se já existem dados de obra
        if db.query(Work).first():
            print("Banco de dados já inicializado")
            return
        
        # Criar obra de exemplo baseada nos FVS reais
        example_work = Work(
            name="Obra Exemplo OBRAX QUANTUM",
            description="Obra modelo com FVS reais para testes de painel e medições",
            work_type=WorkType.BUILDING,
            location="Itajaí - SC",
            progress_percentage=0.0
        )
        db.add(example_work)
        db.commit()
        db.refresh(example_work)
        
        # Criar atividades de exemplo
        example_activities = [
            Activity(
                work_id=example_work.id,
                name="Execução de alvenaria estrutural - Pavimento Tipo 01",
                description="Execução das paredes estruturais, com blocos aparentes, FVS vinculados.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.HIGH,
                progress_percentage=0.0,
                responsible_user="Encarregado João Silva",
                estimated_hours=120.0
            ),
            Activity(
                work_id=example_work.id,
                name="Instalação de fôrmas para laje",
                description="Montagem de fôrmas metálicas e verificação de travamentos.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.MEDIUM,
                progress_percentage=0.0,
                responsible_user="Encarregado Maria Souza",
                estimated_hours=60.0
            ),
            Activity(
                work_id=example_work.id,
                name="Concretagem de laje - Trecho A",
                description="Lançamento de concreto com controle de abatimento e FVS associados.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.HIGH,
                progress_percentage=0.0,
                responsible_user="Equipe Concreto",
                estimated_hours=40.0
            ),
            Activity(
                work_id=example_work.id,
                name="Revisão de armaduras - Pavimento Tipo 02",
                description="Conferência de diâmetros, espaçamentos e posicionamento de ferragens.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.MEDIUM,
                progress_percentage=0.0,
                responsible_user="Encarregado Carlos Lima",
                estimated_hours=30.0
            ),
            Activity(
                work_id=example_work.id,
                name="Vistoria de segurança - Semana 01",
                description="Checklist de FVS de segurança no pavimento em execução.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.LOW,
                progress_percentage=0.0,
                responsible_user="Técnico de Segurança",
                estimated_hours=20.0
            ),
            Activity(
                work_id=example_work.id,
                name="Montagem de andaimes fachada norte",
                description="Montagem e verificação de estabilidade dos andaimes.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.MEDIUM,
                progress_percentage=0.0,
                responsible_user="Equipe Andaimes",
                estimated_hours=50.0
            ),
            Activity(
                work_id=example_work.id,
                name="Instalação de caixilhos - Torre A",
                description="Colocação dos caixilhos de alumínio e vedação inicial.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.LOW,
                progress_percentage=0.0,
                responsible_user="Equipe Esquadrias",
                estimated_hours=70.0
            ),
            Activity(
                work_id=example_work.id,
                name="Medição de serviços executados - Semana 01",
                description="Medição parcial dos serviços executados para conferência com FPM.",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.LOW,
                progress_percentage=0.0,
                responsible_user="Engenharia de Obra",
                estimated_hours=35.0
            )
        ]
        
        for activity in example_activities:
            db.add(activity)
        
        db.commit()
        print("Banco de dados inicializado com dados de exemplo")
        
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
