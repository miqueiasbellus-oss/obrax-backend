import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Lê a variável de ambiente DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./obrax_quantum.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
