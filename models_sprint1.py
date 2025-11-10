from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON, Float, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Enums específicos do Sprint 1
class StatusAtividade(str, Enum):
    PLANNED = "PLANNED"
    READY = "READY"
    IN_EXECUTION = "IN_EXECUTION"
    INSPECTION_PENDING = "INSPECTION_PENDING"
    INSPECTED_PASS = "INSPECTED_PASS"
    INSPECTED_FAIL = "INSPECTED_FAIL"
    PARTIAL_CLOSED = "PARTIAL_CLOSED"
    CLOSED = "CLOSED"
    REWORK = "REWORK"

class TipoEvento(str, Enum):
    PARADO = "PARADO"
    IN_EXECUTION = "IN_EXECUTION"
    PARCIAL_SOLICITADA = "PARCIAL_SOLICITADA"
    FINAL_SOLICITADO = "FINAL_SOLICITADO"
    FVS_PASS = "FVS_PASS"
    FVS_FAIL = "FVS_FAIL"
    NC_ABERTA = "NC_ABERTA"
    DIFICULDADE_ENVIADA = "DIFICULDADE_ENVIADA"

class StatusMedicao(str, Enum):
    PENDENTE = "PENDENTE"
    ACEITA = "ACEITA"
    AJUSTADA = "AJUSTADA"
    RECUSADA = "RECUSADA"

class AcaoRapida(str, Enum):
    PARADO = "PARADO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    PARCIAL = "PARCIAL"
    FINALIZADO = "FINALIZADO"

# ==================== MODELOS SQLALCHEMY ====================

class Programacao(Base):
    __tablename__ = "programacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    quinzena = Column(String(20), nullable=False, index=True)  # Ex: "2024-Q1-1"
    data_publicacao = Column(DateTime)
    autor_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    atividades = relationship("ProgramacaoAtividade", back_populates="programacao", cascade="all, delete-orphan")

class ProgramacaoAtividade(Base):
    __tablename__ = "programacao_atividades"
    
    id = Column(Integer, primary_key=True, index=True)
    programacao_id = Column(Integer, ForeignKey("programacoes.id"), nullable=False)
    
    # Campos conforme especificação
    codigo = Column(String(50), nullable=False, index=True)  # Ex: "ATV-2025-0012"
    encarregado_id = Column(String(255), nullable=False, index=True)
    grupo = Column(String(100))  # disciplina/grupo de serviço
    atividade = Column(String(255), nullable=False)  # nome exibido
    pavimento = Column(String(100))  # Ex: "Pavimento 05"
    local = Column(Text)
    ifs_object_id = Column(String(100))  # vinculado ao objeto 3D
    
    # Prazos
    prazo_inicio = Column(DateTime)
    prazo_fim = Column(DateTime)
    
    # Progresso
    perc_prog_anterior = Column(Float, default=0.0)  # 0-100
    perc_prog_atual = Column(Float, default=0.0)  # 0-100
    
    # Observações
    motivo_atraso = Column(Text)
    observacoes = Column(Text)
    
    # Mídia e IA
    audios_orientacao = Column(JSON)  # Lista de URLs/paths dos áudios
    ai_refs = Column(JSON)  # Links/refs geradas pela IA
    
    # Status atual
    status = Column(SQLEnum(StatusAtividade), default=StatusAtividade.PLANNED)
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    programacao = relationship("Programacao", back_populates="atividades")
    eventos = relationship("AtividadeEvento", back_populates="atividade", cascade="all, delete-orphan")
    fvs_resultados = relationship("FVSResultado", back_populates="atividade", cascade="all, delete-orphan")
    medicoes = relationship("Medicao", back_populates="atividade", cascade="all, delete-orphan")

class AtividadeEvento(Base):
    __tablename__ = "atividade_eventos"
    
    id = Column(Integer, primary_key=True, index=True)
    atividade_id = Column(Integer, ForeignKey("programacao_atividades.id"), nullable=False)
    tipo = Column(SQLEnum(TipoEvento), nullable=False)
    
    # Payload flexível para diferentes tipos de evento
    payload = Column(JSON)  # {observacao, motivo_atraso, percentual, midia[], etc}
    
    # Metadados
    autor_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    atividade = relationship("ProgramacaoAtividade", back_populates="eventos")

class FVSResultado(Base):
    __tablename__ = "fvs_resultados"
    
    id = Column(Integer, primary_key=True, index=True)
    atividade_id = Column(Integer, ForeignKey("programacao_atividades.id"), nullable=False)
    
    # Resultado do FVS
    resultado = Column(String(10), nullable=False)  # PASS ou FAIL
    itens_verificados = Column(JSON)  # Lista de itens do checklist
    fotos_evidencia = Column(JSON)  # URLs das fotos obrigatórias
    tolerancias_ok = Column(Boolean, default=True)
    
    # Observações
    observacoes = Column(Text)
    nc_gerada = Column(String(100))  # ID da NC se FAIL
    
    # Metadados
    inspetor_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    atividade = relationship("ProgramacaoAtividade", back_populates="fvs_resultados")

class Medicao(Base):
    __tablename__ = "medicoes"
    
    id = Column(Integer, primary_key=True, index=True)
    atividade_id = Column(Integer, ForeignKey("programacao_atividades.id"), nullable=False)
    
    # Dados da medição
    percentual_solicitado = Column(Float, nullable=False)  # % proposto pelo encarregado
    percentual_aceito = Column(Float)  # % aceito pelo engenheiro
    status = Column(SQLEnum(StatusMedicao), default=StatusMedicao.PENDENTE)
    
    # Observações
    observacao_encarregado = Column(Text)
    justificativa_engenheiro = Column(Text)
    
    # Tipo de medição
    is_final = Column(Boolean, default=False)  # True = medição final, False = parcial
    
    # Metadados
    solicitante_id = Column(String(255), nullable=False)  # encarregado
    avaliador_id = Column(String(255))  # engenheiro
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    data_avaliacao = Column(DateTime)
    
    # Relacionamentos
    atividade = relationship("ProgramacaoAtividade", back_populates="medicoes")

class DiarioObra(Base):
    __tablename__ = "diario_obras"
    
    id = Column(Integer, primary_key=True, index=True)
    atividade_id = Column(Integer, ForeignKey("programacao_atividades.id"))
    
    # Conteúdo
    data = Column(DateTime, default=datetime.utcnow)
    texto = Column(Text, nullable=False)
    midia = Column(JSON)  # URLs de fotos/áudios/vídeos
    
    # Metadados
    autor_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notificacao(Base):
    __tablename__ = "notificacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    destinatario_id = Column(String(255), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)
    payload = Column(JSON)  # Dados específicos da notificação
    lida = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==================== MODELOS PYDANTIC ====================

class ProgramacaoCreate(BaseModel):
    quinzena: str = Field(..., min_length=1)
    autor_id: str = Field(..., min_length=1)

class ProgramacaoAtividadeCreate(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50)
    encarregado_id: str = Field(..., min_length=1)
    grupo: Optional[str] = None
    atividade: str = Field(..., min_length=1)
    pavimento: Optional[str] = None
    local: Optional[str] = None
    ifs_object_id: Optional[str] = None
    prazo_inicio: Optional[datetime] = None
    prazo_fim: Optional[datetime] = None
    perc_prog_anterior: float = Field(0.0, ge=0, le=100)
    perc_prog_atual: float = Field(0.0, ge=0, le=100)
    motivo_atraso: Optional[str] = None
    observacoes: Optional[str] = None

class ProgramacaoAtividadeResponse(BaseModel):
    id: int
    codigo: str
    encarregado_id: str
    grupo: Optional[str]
    atividade: str
    pavimento: Optional[str]
    local: Optional[str]
    ifs_object_id: Optional[str]
    prazo_inicio: Optional[datetime]
    prazo_fim: Optional[datetime]
    perc_prog_anterior: float
    perc_prog_atual: float
    motivo_atraso: Optional[str]
    observacoes: Optional[str]
    audios_orientacao: Optional[List[str]]
    ai_refs: Optional[List[str]]
    status: StatusAtividade
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AtualizacaoRapidaRequest(BaseModel):
    acao: AcaoRapida
    motivo_atraso: Optional[str] = None
    percentual_para_pagar: Optional[float] = Field(None, ge=0, le=100)
    observacao: Optional[str] = None

class FVSRequest(BaseModel):
    itens_verificados: List[Dict[str, Any]]
    fotos_evidencia: List[str]
    tolerancias_ok: bool = True
    observacoes: Optional[str] = None

class FVSResponse(BaseModel):
    id: int
    resultado: str  # PASS ou FAIL
    itens_verificados: List[Dict[str, Any]]
    fotos_evidencia: List[str]
    tolerancias_ok: bool
    observacoes: Optional[str]
    nc_gerada: Optional[str]
    inspetor_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class MedicaoDecisaoRequest(BaseModel):
    acao: str  # ACEITAR, AJUSTAR, RECUSAR
    percentual: Optional[float] = Field(None, ge=0, le=100)
    justificativa: Optional[str] = None

class MedicaoResponse(BaseModel):
    id: int
    percentual_solicitado: float
    percentual_aceito: Optional[float]
    status: StatusMedicao
    observacao_encarregado: Optional[str]
    justificativa_engenheiro: Optional[str]
    is_final: bool
    solicitante_id: str
    avaliador_id: Optional[str]
    data_solicitacao: datetime
    data_avaliacao: Optional[datetime]
    
    class Config:
        from_attributes = True

class DificuldadeRequest(BaseModel):
    mensagem: Optional[str] = None
    audio_url: Optional[str] = None

class NotificacaoResponse(BaseModel):
    id: int
    tipo: str
    payload: Dict[str, Any]
    lida: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Modelo para resumo do encarregado
class AtividadeEncarregadoSummary(BaseModel):
    id: int
    codigo: str
    atividade: str
    pavimento: Optional[str]
    local: Optional[str]
    prazo_inicio: Optional[datetime]
    prazo_fim: Optional[datetime]
    perc_prog_anterior: float
    perc_prog_atual: float
    status: StatusAtividade
    audios_orientacao: Optional[List[str]]
    ai_refs: Optional[List[str]]
    dias_atraso: Optional[int] = None

