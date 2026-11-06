"""
Schémas Pydantic (validation d'entrée des endpoints FastAPI) - Phase 4.

Pydantic valide d'abord la FORME des données (types, présence des champs
obligatoires) ; les RÈGLES MÉTIER (montant > 0 et cohérence avec le statut,
existence d'une caisse...) restent dans services/ - double niveau de
validation volontaire, pas redondant : l'API rejette vite les requêtes mal
formées, les services protègent la cohérence métier même si l'API est
contournée (tests directs, scripts...).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class UtilisateurCreation(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    mot_de_passe: str = Field(min_length=1)
    nom_complet: str = Field(min_length=1, max_length=100)
    role: Literal["USER", "MANAGER"] = "USER"


class ReinitialisationMotDePasse(BaseModel):
    nouveau_mot_de_passe: str = Field(min_length=1)
    utilisateur_id: int


class ParametreCreation(BaseModel):
    categorie: str = Field(min_length=1, max_length=30)
    code: str = Field(min_length=1, max_length=30)
    libelle: str = Field(min_length=1, max_length=100)


class CaisseCreation(BaseModel):
    code_caisse: str = Field(min_length=1, max_length=20)
    nom_caisse: str = Field(min_length=1, max_length=100)
    societe: str = Field(min_length=1, max_length=50)
    solde_initial: float = 0
    numero_caisse_sage: Optional[int] = None
    compte_financier: Optional[str] = Field(default=None, max_length=13)
    responsable_caisse: Optional[int] = None
    devise: str = Field(default="EUR", max_length=3)


class OperationCreation(BaseModel):
    type_operation: Literal["ALIMENTATION", "DEPENSE", "REMBOURSEMENT"]
    id_caisse: int
    date_operation: datetime
    montant: float = Field(gt=0)
    cree_par: int
    sens_solde: Optional[Literal["ENTREE", "SORTIE"]] = None
    id_motif: Optional[int] = None
    beneficiaire: Optional[str] = Field(default=None, max_length=17)
    responsable: Optional[int] = None
    societe: Optional[str] = Field(default=None, max_length=50)
    compte_financier: Optional[str] = Field(default=None, max_length=13)
    compte_analytique: Optional[str] = Field(default=None, max_length=20)
    devise: str = Field(default="EUR", max_length=3)
    projet: Optional[str] = Field(default=None, max_length=100)
    observation: Optional[str] = Field(default=None, max_length=500)


class OperationModification(BaseModel):
    """Seuls les champs fournis sont modifiés (voir service_operations.modifier_operation)."""

    utilisateur_id: int
    montant: Optional[float] = Field(default=None, gt=0)
    projet: Optional[str] = Field(default=None, max_length=100)
    observation: Optional[str] = Field(default=None, max_length=500)
    beneficiaire: Optional[str] = Field(default=None, max_length=17)
    responsable: Optional[int] = None
    compte_financier: Optional[str] = Field(default=None, max_length=13)
    compte_analytique: Optional[str] = Field(default=None, max_length=20)

    def vers_champs_sql(self) -> dict:
        """Convertit vers les noms de colonnes réels (Montant, Projet...), en ignorant les champs non fournis (et utilisateur_id, passé séparément)."""
        correspondance = {
            "montant": "Montant", "projet": "Projet", "observation": "Observation",
            "beneficiaire": "Beneficiaire", "responsable": "Responsable",
            "compte_financier": "Compte_Financier", "compte_analytique": "Compte_Analytique",
        }
        return {
            correspondance[champ]: valeur
            for champ, valeur in self.model_dump(exclude_unset=True).items()
            if champ in correspondance
        }


class ActionWorkflow(BaseModel):
    """Corps commun aux actions de workflow (Valider/Annuler/Comptabiliser/Remettre en brouillon)."""

    utilisateur_id: int
    commentaire: Optional[str] = Field(default=None, max_length=500)


class ActionComptabilisation(ActionWorkflow):
    reference_comptable_sage: Optional[int] = None


class ModeEcritureModification(BaseModel):
    """Phase 4 (point 1 historique) : interrupteur lecture seule, sans toucher .env ni redémarrer."""

    actif: bool


class ConnexionUtilisateur(BaseModel):
    """Phase 7 : authentification réelle (remplace le sélecteur provisoire)."""

    login: str = Field(min_length=1)
    mot_de_passe: str = Field(min_length=1)
