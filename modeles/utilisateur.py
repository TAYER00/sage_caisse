"""
Modèle UTILISATEURS - comptes applicatifs (login, rôle USER/MANAGER).

Correspond exactement à la table créée en Phase 3
(00_analyse/04_SCHEMA_SAGE_CAISSE.sql), vérifiée réellement sur le serveur.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class Utilisateur(Base):
    __tablename__ = "UTILISATEURS"

    Id_Utilisateur: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Login: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    Mot_De_Passe_Hash: Mapped[str] = mapped_column(String(255), nullable=False)
    Nom_Complet: Mapped[str] = mapped_column(String(100), nullable=False)
    Role: Mapped[str] = mapped_column(String(10), nullable=False, default="USER")
    Actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    Date_Creation: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
