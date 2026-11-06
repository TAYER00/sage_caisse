"""
Modèle CORRESPONDANCE_REGLEMENTS - lien futur avec un vrai règlement Sage
(mode intégré, pas utilisé en mode autonome). Non exploité avant qu'un
mode intégré Sage ne soit explicitement étudié et autorisé.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class CorrespondanceReglement(Base):
    __tablename__ = "CORRESPONDANCE_REGLEMENTS"
    __table_args__ = (UniqueConstraint("Id_Operation", name="UQ_CorrespondanceReglements_Operation"),)

    Id_Correspondance: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Operation: Mapped[int] = mapped_column(Integer, ForeignKey("OPERATIONS_CAISSE.Id_Operation"), nullable=False)
    RG_No_Sage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    EC_No_Sage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Statut_Correspondance: Mapped[str] = mapped_column(String(20), nullable=False, default="NON_LIE")
    Date_Mise_A_Jour: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
