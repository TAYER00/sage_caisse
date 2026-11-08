"""
Modèle TIERS_SAGE - miroir en lecture de F_COMPTET (Phase 12, prompt
utilisateur : remplacer le champ libre "Bénéficiaire (code tiers Sage)"
par une combobox de noms réels).

Table purement un miroir de référentiel : aucune donnée propre à
l'application, entièrement réécrite à chaque synchronisation (voir
services/service_synchronisation_referentiels.py) - contrairement à
CAISSES, il n'y a ici aucun champ "local" à préserver.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class TiersSage(Base):
    __tablename__ = "TIERS_SAGE"

    CT_Num: Mapped[str] = mapped_column(String(17), primary_key=True)
    Intitule: Mapped[str] = mapped_column(String(69), nullable=False)
    Type_Tiers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Derniere_Synchro_Sage: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
