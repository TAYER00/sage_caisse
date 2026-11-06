"""Modèle JUSTIFICATIFS_CAISSE - pièces jointes d'une opération."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class JustificatifCaisse(Base):
    __tablename__ = "JUSTIFICATIFS_CAISSE"

    Id_Justificatif: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Id_Operation: Mapped[int] = mapped_column(Integer, ForeignKey("OPERATIONS_CAISSE.Id_Operation"), nullable=False)
    Nom_Fichier: Mapped[str] = mapped_column(String(255), nullable=False)
    Chemin_Fichier: Mapped[str] = mapped_column(String(500), nullable=False)
    Type_Fichier: Mapped[str] = mapped_column(String(10), nullable=False)
    Taille_Octets: Mapped[int] = mapped_column(Integer, nullable=False)
    Supprime: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    Date_Ajout: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    Ajoute_Par: Mapped[int] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=False)
