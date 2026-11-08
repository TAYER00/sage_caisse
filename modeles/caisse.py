"""
Modèle CAISSES.

Les références à Sage (Numero_Caisse_Sage -> F_CAISSE.CA_No,
Compte_Financier -> F_COMPTEG.CG_Num, Responsable_Caisse ->
F_COLLABORATEUR.CO_No) restent de simples colonnes : aucune contrainte de
clé étrangère physique vers Sage (bases différentes, voir
00_analyse/04_PHASE3_SCHEMA_APPLICATIF.md section 1).

Solde_Actuel est un CACHE recalculé par le code métier (Phase 5) à partir
des opérations - jamais modifié directement ici.

Phase 11 (prompt_4.txt) : Numero_Caisse_Sage devient la clé d'appariement
de la synchronisation depuis BIJOU (contrainte UNIQUE - SQL Server
autorise plusieurs NULL sous une contrainte UNIQUE, donc une caisse
100% applicative sans lien Sage reste possible). Derniere_Synchro_Sage
trace la dernière fois que cette caisse a été mise à jour par
service_synchronisation_caisses.py (voir 00_analyse/11_PHASE1_ANALYSE_SYNC_BIJOU.md).
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from modeles.base import Base


class Caisse(Base):
    __tablename__ = "CAISSES"
    __table_args__ = (
        UniqueConstraint("Code_Caisse", name="UQ_Caisses_Code"),
        UniqueConstraint("Numero_Caisse_Sage", name="UQ_Caisses_NumeroCaisseSage"),
    )

    Id_Caisse: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    Code_Caisse: Mapped[str] = mapped_column(String(20), nullable=False)
    Nom_Caisse: Mapped[str] = mapped_column(String(100), nullable=False)
    Societe: Mapped[str] = mapped_column(String(50), nullable=False)
    Numero_Caisse_Sage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Compte_Financier: Mapped[str | None] = mapped_column(String(13), nullable=True)
    Responsable_Caisse: Mapped[int | None] = mapped_column(Integer, nullable=True)
    Devise: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    Solde_Initial: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    Solde_Actuel: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    Statut: Mapped[str] = mapped_column(String(10), nullable=False, default="ACTIF")
    Date_Creation: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    Derniere_Synchro_Sage: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
