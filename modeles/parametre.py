"""
Modèle PARAMETRES_CAISSE - listes dynamiques (motifs, etc.).

Règle du prompt : jamais de suppression physique si déjà utilisée -
seulement Actif = False (voir services/service_parametres.py).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class ParametreCaisse(Base):
    __tablename__ = "PARAMETRES_CAISSE"
    __table_args__ = (UniqueConstraint("Categorie", "Code", name="UQ_ParametresCaisse_CategorieCode"),)

    Id_Parametre: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Categorie: Mapped[str] = mapped_column(String(30), nullable=False)
    Code: Mapped[str] = mapped_column(String(30), nullable=False)
    Libelle: Mapped[str] = mapped_column(String(100), nullable=False)
    Actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    Date_Creation: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
