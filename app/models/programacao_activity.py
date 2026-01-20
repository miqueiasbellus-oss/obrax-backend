class ProgramacaoActivity(Base):
    __tablename__ = "programacao_activities"

    id = Column(Integer, primary_key=True)

    programacao_id = Column(Integer, ForeignKey("programacoes.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)

    encarregado_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    predecessor_user_id = Column(Integer, ForeignKey("users.id"))

    audio_eng = Column(String)
    audio_mestre = Column(String)
    location_ref = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
