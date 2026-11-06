"""Modèle VALIDATIONS_CAISSE - historique des actions de workflow (Phase 5)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class ValidationCaisse(Base):
    __tablename__ = "VALIDATIONS_CAISSE"

    Id_Validation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Operation: Mapped[int] = mapped_column(Integer, ForeignKey("OPERATIONS_CAISSE.Id_Operation"), nullable=False)
    Action: Mapped[str] = mapped_column(String(20), nullable=False)
    Utilisateur: Mapped[int] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=False)
    Date_Action: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    Commentaire: Mapped[str | None] = mapped_column(String(500), nullable=True)
