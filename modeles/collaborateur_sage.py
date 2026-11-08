"""
Modèle COLLABORATEURS_SAGE - miroir en lecture de F_COLLABORATEUR (Phase
12, prompt utilisateur : remplacer le champ libre "Responsable (code
collaborateur Sage)" par une combobox de noms réels).

Table purement un miroir de référentiel : aucune donnée propre à
l'application, entièrement réécrite à chaque synchronisation (voir
services/service_synchronisation_referentiels.py).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class CollaborateurSage(Base):
    __tablename__ = "COLLABORATEURS_SAGE"

    # autoincrement=False : CO_No est l'identifiant REEL Sage (F_COLLABORATEUR.CO_No),
    # pas une IDENTITY SQL Server - sans ce réglage, SQLAlchemy tente par défaut un
    # SET IDENTITY_INSERT sur une colonne qui n'en a pas (erreur réelle rencontrée).
    CO_No: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    Nom_Complet: Mapped[str] = mapped_column(String(80), nullable=False)
    Caissier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Derniere_Synchro_Sage: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
