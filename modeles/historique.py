"""Modèle HISTORIQUE_CAISSE - traçabilité champ par champ (Phase 5)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class HistoriqueCaisse(Base):
    __tablename__ = "HISTORIQUE_CAISSE"

    Id_Historique: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Operation: Mapped[int] = mapped_column(Integer, ForeignKey("OPERATIONS_CAISSE.Id_Operation"), nullable=False)
    Champ_Modifie: Mapped[str] = mapped_column(String(50), nullable=False)
    Ancienne_Valeur: Mapped[str | None] = mapped_column(String(500), nullable=True)
    Nouvelle_Valeur: Mapped[str | None] = mapped_column(String(500), nullable=True)
    Utilisateur: Mapped[int] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=False)
    Date_Modification: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
