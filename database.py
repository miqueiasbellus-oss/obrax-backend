import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./obrax_quantum.db")

# Para PostgreSQL em produção, use:
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Miqueia$6969@db.tpgnxxndpcaxfipbieme.supabase.co:5432/postgres"

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
    
    db = SessionLocal()
    
    try:
        # Verificar se já existem dados
        if db.query(Work).first():
            print("Banco de dados já inicializado")
            return
        
        # Criar obra de exemplo baseada nos FVS reais
        example_work = Work(
            name="Residencial Vila Nova",
            description="Construção de residencial unifamiliar com 3 pavimentos",
            work_type=WorkType.CONSTRUCTION,
            client_name="Construtora ABC Ltda",
            location="Rua das Flores, 123 - São Paulo/SP",
            budget=850000.00
        )
        
        db.add(example_work)
        db.commit()
        db.refresh(example_work)
        
        # Criar atividades de exemplo baseadas nos FVS analisados
        example_activities = [
            Activity(
                work_id=example_work.id,
                name="Locação da Obra",
                description="Marcação e locação dos elementos estruturais",
                ifs_code="PE00101_FS00203",
                discipline="Infraestrutura",
                front="Térreo",
                service_type="Locação",
                status=ActivityStatus.CLOSED,
                priority=ActivityPriority.HIGH,
                progress_percentage=100.0,
                responsible_user="João Silva",
                estimated_hours=16.0,
                actual_hours=14.0
            ),
            Activity(
                work_id=example_work.id,
                name="Execução de Radier",
                description="Execução de radier em concreto armado",
                ifs_code="PE00201_FS00303",
                discipline="Infraestrutura",
                front="Térreo",
                service_type="Fundação",
                status=ActivityStatus.CLOSED,
                priority=ActivityPriority.HIGH,
                progress_percentage=100.0,
                responsible_user="Carlos Santos",
                estimated_hours=40.0,
                actual_hours=38.0
            ),
            Activity(
                work_id=example_work.id,
                name="Alvenaria de Vedação - Casa",
                description="Execução de alvenaria de vedação em blocos cerâmicos",
                ifs_code="PE01201_FS01403",
                discipline="Alvenaria",
                front="Térreo",
                service_type="Alvenaria de Vedação",
                status=ActivityStatus.IN_EXECUTION,
                priority=ActivityPriority.MEDIUM,
                progress_percentage=65.0,
                responsible_user="Maria Oliveira",
                estimated_hours=80.0,
                actual_hours=52.0
            ),
            Activity(
                work_id=example_work.id,
                name="Revestimento em Argamassa",
                description="Aplicação de revestimento interno em argamassa",
                ifs_code="PE01401_FS01603",
                discipline="Revestimento",
                front="Térreo",
                service_type="Revestimento Argamassa",
                status=ActivityStatus.PCC_REQUIRED,
                priority=ActivityPriority.MEDIUM,
                progress_percentage=0.0,
                responsible_user="Ana Costa",
                estimated_hours=60.0
            ),
            Activity(
                work_id=example_work.id,
                name="Instalações Elétricas",
                description="Execução de instalações elétricas internas",
                ifs_code="FS02703",
                discipline="Instalações",
                front="Térreo",
                service_type="Instalações Elétricas",
                status=ActivityStatus.READY,
                priority=ActivityPriority.HIGH,
                progress_percentage=0.0,
                responsible_user="Pedro Lima",
                estimated_hours=45.0
            ),
            Activity(
                work_id=example_work.id,
                name="Pintura Látex PVA",
                description="Aplicação de pintura látex PVA em paredes internas",
                ifs_code="PE02501_FS02603",
                discipline="Acabamento",
                front="Térreo",
                service_type="Pintura",
                status=ActivityStatus.PLANNED,
                priority=ActivityPriority.LOW,
                progress_percentage=0.0,
                responsible_user="Luiza Santos",
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

