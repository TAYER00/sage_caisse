"""
Modèle OPERATIONS_CAISSE - table centrale du projet.

Phase 4 : CRUD de base uniquement (création en BROUILLON, lecture,
modification des champs, suppression d'un brouillon). Les transitions de
statut (Valider/Annuler/Comptabiliser/Remettre en brouillon) et le calcul
du solde sont la Phase 5 - volontairement pas ici.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class OperationCaisse(Base):
    __tablename__ = "OPERATIONS_CAISSE"
    __table_args__ = (UniqueConstraint("Reference", name="UQ_OperationsCaisse_Reference"),)

    Id_Operation: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Reference: Mapped[str] = mapped_column(String(20), nullable=False)
    Type_Operation: Mapped[str] = mapped_column(String(15), nullable=False)
    Sens_Solde: Mapped[str] = mapped_column(String(7), nullable=False)
    Id_Caisse: Mapped[int] = mapped_column(Integer, ForeignKey("CAISSES.Id_Caisse"), nullable=False)
    Date_Operation: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    Id_Motif: Mapped[int | None] = mapped_column(Integer, ForeignKey("PARAMETRES_CAISSE.Id_Parametre"), nullable=True)
    Beneficiaire: Mapped[str | None] = mapped_column(String(17), nullable=True)
    Responsable: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Societe: Mapped[str | None] = mapped_column(String(50), nullable=True)
    Compte_Financier: Mapped[str | None] = mapped_column(String(13), nullable=True)
    Compte_Analytique: Mapped[str | None] = mapped_column(String(20), nullable=True)
    Montant: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    Devise: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    Projet: Mapped[str | None] = mapped_column(String(100), nullable=True)
    Observation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    Statut: Mapped[str] = mapped_column(String(15), nullable=False, default="BROUILLON")
    Cree_Par: Mapped[int] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=False)
    Date_Creation: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    Modifie_Par: Mapped[int | None] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=True)
    Date_Modification: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Valide_Par: Mapped[int | None] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=True)
    Date_Validation: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Comptabilise_Par: Mapped[int | None] = mapped_column(Integer, ForeignKey("UTILISATEURS.Id_Utilisateur"), nullable=True)
    Date_Comptabilisation: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    Reference_Comptable_Sage: Mapped[int | None] = mapped_column(Integer, nullable=True)
