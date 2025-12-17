from fastapi import FastAPI, HTTPException, Depends, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import json

from database import get_db
from models import (
    Activity, ActivityStatus, ActivityPriority,
    EventPCC, EventFVS, EventNC,
    FVSStatus, NCOrigin, NCStatus
)
# TODO: Sprint 1 models need to be migrated to models.py following Activity pattern

# ==================== PROGRAMAÇÃO QUINZENAL ====================

def create_programacao_endpoints(app: FastAPI):
    
    @app.post("/programacao/quinzena")
    async def criar_programacao(programacao: ProgramacaoCreate, db: Session = Depends(get_db)):
        """Criar nova programação quinzenal"""
        db_programacao = Programacao(**programacao.dict())
        db.add(db_programacao)
        db.commit()
        db.refresh(db_programacao)
        return db_programacao

    @app.post("/programacao/quinzena/{programacao_id}/publicar")
    async def publicar_programacao(programacao_id: int, db: Session = Depends(get_db)):
        """Publicar programação e notificar encarregados"""
        programacao = db.query(Programacao).filter(Programacao.id == programacao_id).first()
        if not programacao:
            raise HTTPException(status_code=404, detail="Programação não encontrada")
        
        # Atualizar data de publicação
        programacao.data_publicacao = datetime.utcnow()
        
        # Buscar encarregados únicos
        atividades = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.programacao_id == programacao_id
        ).all()
        
        encarregados = list(set([a.encarregado_id for a in atividades]))
        
        # Criar notificações
        for encarregado_id in encarregados:
            notificacao = Notificacao(
                destinatario_id=encarregado_id,
                tipo="PROGRAMACAO_PUBLICADA",
                payload={
                    "programacao_id": programacao_id,
                    "quinzena": programacao.quinzena,
                    "total_atividades": len([a for a in atividades if a.encarregado_id == encarregado_id])
                }
            )
            db.add(notificacao)
        
        db.commit()
        return {"message": f"Programação publicada para {len(encarregados)} encarregados"}

    @app.get("/programacao/atividades", response_model=List[ProgramacaoAtividadeResponse])
    async def get_atividades_programacao(
        quinzena: Optional[str] = None,
        encarregado_id: Optional[str] = None,
        db: Session = Depends(get_db)
    ):
        """Listar atividades da programação com filtros"""
        query = db.query(ProgramacaoAtividade)
        
        if quinzena:
            # Buscar programação da quinzena
            programacao = db.query(Programacao).filter(Programacao.quinzena == quinzena).first()
            if programacao:
                query = query.filter(ProgramacaoAtividade.programacao_id == programacao.id)
        
        if encarregado_id:
            query = query.filter(ProgramacaoAtividade.encarregado_id == encarregado_id)
        
        atividades = query.all()
        return atividades

    @app.post("/programacao/{programacao_id}/atividades")
    async def adicionar_atividade(
        programacao_id: int, 
        atividade: ProgramacaoAtividadeCreate, 
        db: Session = Depends(get_db)
    ):
        """Adicionar atividade à programação"""
        # Verificar se programação existe
        programacao = db.query(Programacao).filter(Programacao.id == programacao_id).first()
        if not programacao:
            raise HTTPException(status_code=404, detail="Programação não encontrada")
        
        db_atividade = ProgramacaoAtividade(
            programacao_id=programacao_id,
            **atividade.dict()
        )
        db.add(db_atividade)
        db.commit()
        db.refresh(db_atividade)
        return db_atividade

    @app.post("/atividade/{atividade_id}/audio")
    async def upload_audio_orientacao(
        atividade_id: int,
        audio: UploadFile = File(...),
        db: Session = Depends(get_db)
    ):
        """Upload de áudio de orientação para atividade"""
        atividade = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.id == atividade_id
        ).first()
        if not atividade:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        
        # Simular salvamento do arquivo (em produção, salvar no storage)
        audio_url = f"/uploads/audios/{atividade_id}_{datetime.utcnow().timestamp()}.mp3"
        
        # Adicionar à lista de áudios
        if not atividade.audios_orientacao:
            atividade.audios_orientacao = []
        
        audios = atividade.audios_orientacao or []
        audios.append(audio_url)
        atividade.audios_orientacao = audios
        
        db.commit()
        return {"message": "Áudio adicionado", "url": audio_url}

    @app.post("/atividade/{atividade_id}/ai_refs")
    async def gerar_ai_refs(atividade_id: int, db: Session = Depends(get_db)):
        """Gerar referências de IA para atividade"""
        atividade = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.id == atividade_id
        ).first()
        if not atividade:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        
        # Simular geração de referências pela IA
        refs_simuladas = [
            f"NBR 15575 - Desempenho de edificações - {atividade.grupo}",
            f"Manual técnico - {atividade.atividade}",
            f"Procedimento padrão - {atividade.grupo.lower() if atividade.grupo else 'geral'}"
        ]
        
        atividade.ai_refs = refs_simuladas
        db.commit()
        
        return {"message": "Referências geradas", "refs": refs_simuladas}

    # ==================== PAINEL DO ENCARREGADO ====================

    @app.get("/encarregado/{encarregado_id}/atividades", response_model=List[AtividadeEncarregadoSummary])
    async def get_atividades_encarregado(
        encarregado_id: str,
        quinzena: Optional[str] = None,
        db: Session = Depends(get_db)
    ):
        """Listar atividades do encarregado para a quinzena"""
        query = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.encarregado_id == encarregado_id
        )
        
        if quinzena:
            programacao = db.query(Programacao).filter(Programacao.quinzena == quinzena).first()
            if programacao:
                query = query.filter(ProgramacaoAtividade.programacao_id == programacao.id)
        
        # Filtrar apenas atividades não finalizadas para o encarregado
        query = query.filter(ProgramacaoAtividade.status.notin_([
            StatusAtividade.CLOSED, 
            StatusAtividade.PARTIAL_CLOSED
        ]))
        
        atividades = query.all()
        
        # Calcular dias de atraso
        summaries = []
        for atividade in atividades:
            dias_atraso = None
            if atividade.prazo_fim and datetime.utcnow() > atividade.prazo_fim:
                dias_atraso = (datetime.utcnow() - atividade.prazo_fim).days
            
            summaries.append(AtividadeEncarregadoSummary(
                id=atividade.id,
                codigo=atividade.codigo,
                atividade=atividade.atividade,
                pavimento=atividade.pavimento,
                local=atividade.local,
                prazo_inicio=atividade.prazo_inicio,
                prazo_fim=atividade.prazo_fim,
                perc_prog_anterior=atividade.perc_prog_anterior,
                perc_prog_atual=atividade.perc_prog_atual,
                status=atividade.status,
                audios_orientacao=atividade.audios_orientacao,
                ai_refs=atividade.ai_refs,
                dias_atraso=dias_atraso
            ))
        
        return summaries

    @app.post("/atividade/{atividade_id}/dificuldade")
    async def reportar_dificuldade(
        atividade_id: int,
        dificuldade: DificuldadeRequest,
        encarregado_id: str = Query(...),
        db: Session = Depends(get_db)
    ):
        """Reportar dificuldade na atividade"""
        atividade = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.id == atividade_id
        ).first()
        if not atividade:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        
        # Registrar evento
        evento = AtividadeEvento(
            atividade_id=atividade_id,
            tipo=TipoEvento.DIFICULDADE_ENVIADA,
            autor_id=encarregado_id,
            payload={
                "mensagem": dificuldade.mensagem,
                "audio_url": dificuldade.audio_url
            }
        )
        db.add(evento)
        
        # Notificar engenheiro/mestre (simular busca de responsáveis)
        responsaveis = ["engenheiro@obra.com", "mestre@obra.com"]  # Em produção, buscar do BD
        
        for responsavel in responsaveis:
            notificacao = Notificacao(
                destinatario_id=responsavel,
                tipo="DIFICULDADE_REPORTADA",
                payload={
                    "atividade_id": atividade_id,
                    "atividade_nome": atividade.atividade,
                    "encarregado_id": encarregado_id,
                    "mensagem": dificuldade.mensagem,
                    "audio_url": dificuldade.audio_url
                }
            )
            db.add(notificacao)
        
        db.commit()
        return {"message": "Dificuldade reportada aos responsáveis"}

    @app.post("/atividade/{atividade_id}/status")
    async def atualizar_status_rapido(
        atividade_id: int,
        atualizacao: AtualizacaoRapidaRequest,
        encarregado_id: str = Query(...),
        db: Session = Depends(get_db)
    ):
        """Atualização rápida de status da atividade"""
        atividade = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.id == atividade_id
        ).first()
        if not atividade:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        
        # Processar ação
        if atualizacao.acao == AcaoRapida.PARADO:
            # Registrar motivo de parada
            if atividade.prazo_fim and datetime.utcnow() > atividade.prazo_fim and not atualizacao.motivo_atraso:
                raise HTTPException(status_code=400, detail="Motivo de atraso obrigatório para atividades em atraso")
            
            atividade.motivo_atraso = atualizacao.motivo_atraso
            
            # Registrar evento
            evento = AtividadeEvento(
                atividade_id=atividade_id,
                tipo=TipoEvento.PARADO,
                autor_id=encarregado_id,
                payload={
                    "motivo_atraso": atualizacao.motivo_atraso,
                    "observacao": atualizacao.observacao
                }
            )
            db.add(evento)
            
            # Diário
            diario = DiarioObra(
                atividade_id=atividade_id,
                texto=f"Atividade PARADA - Motivo: {atualizacao.motivo_atraso or 'Não informado'}",
                autor_id=encarregado_id
            )
            db.add(diario)
        
        elif atualizacao.acao == AcaoRapida.EM_ANDAMENTO:
            atividade.status = StatusAtividade.IN_EXECUTION
            
            evento = AtividadeEvento(
                atividade_id=atividade_id,
                tipo=TipoEvento.IN_EXECUTION,
                autor_id=encarregado_id,
                payload={"observacao": atualizacao.observacao}
            )
            db.add(evento)
            
            diario = DiarioObra(
                atividade_id=atividade_id,
                texto=f"Início/continuidade da atividade {atividade.atividade} no local {atividade.local or atividade.pavimento}",
                autor_id=encarregado_id
            )
            db.add(diario)
        
        elif atualizacao.acao in [AcaoRapida.PARCIAL, AcaoRapida.FINALIZADO]:
            if not atualizacao.percentual_para_pagar:
                raise HTTPException(status_code=400, detail="Percentual para pagamento obrigatório")
            
            # Criar medição
            medicao = Medicao(
                atividade_id=atividade_id,
                percentual_solicitado=atualizacao.percentual_para_pagar,
                observacao_encarregado=atualizacao.observacao,
                is_final=(atualizacao.acao == AcaoRapida.FINALIZADO),
                solicitante_id=encarregado_id
            )
            db.add(medicao)
            
            # Atualizar status para inspeção pendente
            atividade.status = StatusAtividade.INSPECTION_PENDING
            
            # Registrar evento
            tipo_evento = TipoEvento.FINAL_SOLICITADO if atualizacao.acao == AcaoRapida.FINALIZADO else TipoEvento.PARCIAL_SOLICITADA
            evento = AtividadeEvento(
                atividade_id=atividade_id,
                tipo=tipo_evento,
                autor_id=encarregado_id,
                payload={
                    "percentual": atualizacao.percentual_para_pagar,
                    "observacao": atualizacao.observacao,
                    "is_final": atualizacao.acao == AcaoRapida.FINALIZADO
                }
            )
            db.add(evento)
            
            # Diário
            tipo_texto = "Finalização" if atualizacao.acao == AcaoRapida.FINALIZADO else "Fechamento parcial"
            diario = DiarioObra(
                atividade_id=atividade_id,
                texto=f"{tipo_texto} - {atualizacao.percentual_para_pagar}% - {atualizacao.observacao or 'Sem observações'}",
                autor_id=encarregado_id
            )
            db.add(diario)
            
            # Notificar engenheiro
            notificacao = Notificacao(
                destinatario_id="engenheiro@obra.com",  # Em produção, buscar do BD
                tipo="MEDICAO_SOLICITADA",
                payload={
                    "atividade_id": atividade_id,
                    "atividade_nome": atividade.atividade,
                    "percentual": atualizacao.percentual_para_pagar,
                    "is_final": atualizacao.acao == AcaoRapida.FINALIZADO,
                    "encarregado_id": encarregado_id
                }
            )
            db.add(notificacao)
        
        db.commit()
        return {"message": f"Status atualizado: {atualizacao.acao.value}"}

    # ==================== FVS ====================

    @app.post("/atividade/{atividade_id}/fvs", response_model=FVSResponse)
    async def preencher_fvs(
        atividade_id: int,
        fvs: FVSRequest,
        inspetor_id: str = Query(...),
        db: Session = Depends(get_db)
    ):
        """Preencher FVS da atividade"""
        atividade = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.id == atividade_id
        ).first()
        if not atividade:
            raise HTTPException(status_code=404, detail="Atividade não encontrada")
        
        # Determinar resultado (PASS/FAIL)
        resultado = "PASS" if fvs.tolerancias_ok and len(fvs.fotos_evidencia) > 0 else "FAIL"
        
        # Criar resultado FVS
        fvs_resultado = FVSResultado(
            atividade_id=atividade_id,
            resultado=resultado,
            itens_verificados=fvs.itens_verificados,
            fotos_evidencia=fvs.fotos_evidencia,
            tolerancias_ok=fvs.tolerancias_ok,
            observacoes=fvs.observacoes,
            inspetor_id=inspetor_id
        )
        
        if resultado == "FAIL":
            # Gerar NC
            nc_id = f"NC-{atividade_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
            fvs_resultado.nc_gerada = nc_id
            atividade.status = StatusAtividade.REWORK
            
            # Evento de falha
            evento = AtividadeEvento(
                atividade_id=atividade_id,
                tipo=TipoEvento.FVS_FAIL,
                autor_id=inspetor_id,
                payload={
                    "nc_id": nc_id,
                    "observacoes": fvs.observacoes
                }
            )
            db.add(evento)
            
            # Notificar engenheiro e qualidade
            for destinatario in ["engenheiro@obra.com", "qualidade@obra.com"]:
                notificacao = Notificacao(
                    destinatario_id=destinatario,
                    tipo="FVS_FAIL",
                    payload={
                        "atividade_id": atividade_id,
                        "nc_id": nc_id,
                        "atividade_nome": atividade.atividade
                    }
                )
                db.add(notificacao)
        
        else:
            # FVS passou - liberar para medição
            atividade.status = StatusAtividade.INSPECTED_PASS
            
            evento = AtividadeEvento(
                atividade_id=atividade_id,
                tipo=TipoEvento.FVS_PASS,
                autor_id=inspetor_id,
                payload={"observacoes": fvs.observacoes}
            )
            db.add(evento)
        
        db.add(fvs_resultado)
        db.commit()
        db.refresh(fvs_resultado)
        
        return fvs_resultado

    # ==================== MEDIÇÕES ====================

    @app.get("/engenharia/medicoes", response_model=List[MedicaoResponse])
    async def get_medicoes_pendentes(
        status: StatusMedicao = StatusMedicao.PENDENTE,
        db: Session = Depends(get_db)
    ):
        """Listar medições para aceite do engenheiro"""
        medicoes = db.query(Medicao).filter(Medicao.status == status).all()
        return medicoes

    @app.post("/engenharia/medicao/{medicao_id}/decidir")
    async def decidir_medicao(
        medicao_id: int,
        decisao: MedicaoDecisaoRequest,
        engenheiro_id: str = Query(...),
        db: Session = Depends(get_db)
    ):
        """Aceitar/Ajustar/Recusar medição"""
        medicao = db.query(Medicao).filter(Medicao.id == medicao_id).first()
        if not medicao:
            raise HTTPException(status_code=404, detail="Medição não encontrada")
        
        atividade = db.query(ProgramacaoAtividade).filter(
            ProgramacaoAtividade.id == medicao.atividade_id
        ).first()
        
        medicao.avaliador_id = engenheiro_id
        medicao.data_avaliacao = datetime.utcnow()
        medicao.justificativa_engenheiro = decisao.justificativa
        
        if decisao.acao == "ACEITAR":
            medicao.status = StatusMedicao.ACEITA
            medicao.percentual_aceito = medicao.percentual_solicitado
            
            # Atualizar status da atividade
            if medicao.is_final:
                atividade.status = StatusAtividade.CLOSED
                atividade.perc_prog_atual = 100.0
            else:
                atividade.status = StatusAtividade.PARTIAL_CLOSED
                atividade.perc_prog_atual = medicao.percentual_aceito
        
        elif decisao.acao == "AJUSTAR":
            if not decisao.percentual:
                raise HTTPException(status_code=400, detail="Percentual obrigatório para ajuste")
            
            medicao.status = StatusMedicao.AJUSTADA
            medicao.percentual_aceito = decisao.percentual
            
            if medicao.is_final:
                atividade.status = StatusAtividade.CLOSED
                atividade.perc_prog_atual = 100.0
            else:
                atividade.status = StatusAtividade.PARTIAL_CLOSED
                atividade.perc_prog_atual = medicao.percentual_aceito
        
        elif decisao.acao == "RECUSAR":
            medicao.status = StatusMedicao.RECUSADA
            # Atividade volta para execução
            atividade.status = StatusAtividade.IN_EXECUTION
        
        # Notificar encarregado
        notificacao = Notificacao(
            destinatario_id=medicao.solicitante_id,
            tipo="MEDICAO_DECIDIDA",
            payload={
                "medicao_id": medicao_id,
                "acao": decisao.acao,
                "percentual_aceito": medicao.percentual_aceito,
                "justificativa": decisao.justificativa,
                "atividade_nome": atividade.atividade
            }
        )
        db.add(notificacao)
        
        db.commit()
        return {"message": f"Medição {decisao.acao.lower()}a"}

    # ==================== NOTIFICAÇÕES ====================

    @app.get("/notificacoes/{usuario_id}", response_model=List[NotificacaoResponse])
    async def get_notificacoes(
        usuario_id: str,
        apenas_nao_lidas: bool = False,
        db: Session = Depends(get_db)
    ):
        """Listar notificações do usuário"""
        query = db.query(Notificacao).filter(Notificacao.destinatario_id == usuario_id)
        
        if apenas_nao_lidas:
            query = query.filter(Notificacao.lida == False)
        
        notificacoes = query.order_by(Notificacao.created_at.desc()).limit(50).all()
        return notificacoes

    @app.post("/notificacoes/{notificacao_id}/marcar_lida")
    async def marcar_notificacao_lida(notificacao_id: int, db: Session = Depends(get_db)):
        """Marcar notificação como lida"""
        notificacao = db.query(Notificacao).filter(Notificacao.id == notificacao_id).first()
        if not notificacao:
            raise HTTPException(status_code=404, detail="Notificação não encontrada")
        
        notificacao.lida = True
        db.commit()
        return {"message": "Notificação marcada como lida"}

    return app

