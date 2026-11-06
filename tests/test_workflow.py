"""
Tests du workflow complet (Phase 5) : transitions de statut, droits,
historique, et calcul du solde - voir
00_analyse/05_PHASE5_WORKFLOW.md pour les règles testées ici.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from modeles.historique import HistoriqueCaisse
from modeles.validation import ValidationCaisse
from services import service_caisses, service_operations, service_utilisateurs


@pytest.fixture
def contexte(session_app):
    """Un MANAGER, un USER (créateur) et une caisse à solde initial 500."""
    id_manager = service_utilisateurs.creer_utilisateur("manager", "x", "Manager Test", "MANAGER")["id"]
    id_user = service_utilisateurs.creer_utilisateur("employe", "x", "Employé Test", "USER")["id"]
    id_caisse = service_caisses.creer_caisse("CA-1", "Caisse Test", "Bijou SA", solde_initial=500)["id"]
    return {"id_manager": id_manager, "id_user": id_user, "id_caisse": id_caisse}


def _creer_depense(contexte, montant=100):
    return service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), montant, contexte["id_user"],
    )["id"]


# --- Validation ---------------------------------------------------------------

def test_manager_peut_valider(contexte):
    id_operation = _creer_depense(contexte)
    resultat = service_operations.valider_operation(id_operation, contexte["id_manager"])
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Statut"] == "VALIDE"


def test_user_ne_peut_pas_valider(contexte):
    id_operation = _creer_depense(contexte)
    with pytest.raises(ErreurValidation, match="droits"):
        service_operations.valider_operation(id_operation, contexte["id_user"])


def test_double_validation_refusee(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    with pytest.raises(ErreurValidation, match="déjà été validée"):
        service_operations.valider_operation(id_operation, contexte["id_manager"])


def test_valider_trace_une_ligne_de_validation(contexte, session_app):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"], commentaire="OK")
    lignes = session_app.query(ValidationCaisse).filter(ValidationCaisse.Id_Operation == id_operation).all()
    assert len(lignes) == 1
    assert lignes[0].Action == "VALIDATION"
    assert lignes[0].Utilisateur == contexte["id_manager"]


# --- Annulation -----------------------------------------------------------------

def test_createur_peut_annuler_son_brouillon(contexte):
    id_operation = _creer_depense(contexte)
    resultat = service_operations.annuler_operation(id_operation, contexte["id_user"])
    assert resultat["succes"] is True
    assert service_operations.lire_operation(id_operation)["donnees"]["Statut"] == "ANNULE"


def test_user_ne_peut_pas_annuler_une_operation_validee(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    with pytest.raises(ErreurValidation, match="droits"):
        service_operations.annuler_operation(id_operation, contexte["id_user"])


def test_manager_peut_annuler_une_operation_validee(contexte):
    id_operation = _creer_depense(contexte, montant=100)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    resultat = service_operations.annuler_operation(id_operation, contexte["id_manager"])
    assert resultat["succes"] is True
    # Le solde doit redescendre (l'opération ne compte plus) - voir section solde.
    caisse = service_caisses.lire_caisse(contexte["id_caisse"])["donnees"]
    assert caisse["Solde_Actuel"] == 500  # redevenu le solde initial


def test_comptabilise_ne_peut_pas_etre_annulee(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    service_operations.comptabiliser_operation(id_operation, contexte["id_manager"])
    with pytest.raises(ErreurValidation, match="comptabilisée"):
        service_operations.annuler_operation(id_operation, contexte["id_manager"])


# --- Comptabilisation -----------------------------------------------------------

def test_comptabiliser_une_operation_validee(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    resultat = service_operations.comptabiliser_operation(id_operation, contexte["id_manager"], reference_comptable_sage=316)
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Statut"] == "COMPTABILISE"


def test_comptabiliser_un_brouillon_est_refuse(contexte):
    id_operation = _creer_depense(contexte)
    with pytest.raises(ErreurValidation, match="VALIDE"):
        service_operations.comptabiliser_operation(id_operation, contexte["id_manager"])


def test_user_ne_peut_pas_comptabiliser(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    with pytest.raises(ErreurValidation, match="droits"):
        service_operations.comptabiliser_operation(id_operation, contexte["id_user"])


# --- Remise en brouillon ---------------------------------------------------------

def test_manager_peut_remettre_en_brouillon(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    resultat = service_operations.remettre_en_brouillon(id_operation, contexte["id_manager"])
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Statut"] == "BROUILLON"
    # Redevenue modifiable par son créateur.
    service_operations.modifier_operation(id_operation, contexte["id_user"], Montant=150)


def test_user_ne_peut_pas_remettre_en_brouillon(contexte):
    id_operation = _creer_depense(contexte)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    with pytest.raises(ErreurValidation, match="droits"):
        service_operations.remettre_en_brouillon(id_operation, contexte["id_user"])


# --- Calcul du solde --------------------------------------------------------------

def test_solde_augmente_avec_alimentation_validee(contexte):
    id_operation = service_operations.creer_operation(
        "ALIMENTATION", contexte["id_caisse"], datetime.now(), 200, contexte["id_user"],
    )["id"]
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    caisse = service_caisses.lire_caisse(contexte["id_caisse"])["donnees"]
    assert caisse["Solde_Actuel"] == 700  # 500 + 200


def test_solde_diminue_avec_depense_validee(contexte):
    id_operation = _creer_depense(contexte, montant=80)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    caisse = service_caisses.lire_caisse(contexte["id_caisse"])["donnees"]
    assert caisse["Solde_Actuel"] == 420  # 500 - 80


def test_solde_ignore_les_brouillons_et_annulees(contexte):
    _creer_depense(contexte, montant=999)  # reste en BROUILLON, ne doit pas impacter le solde
    id_annulee = _creer_depense(contexte, montant=50)
    service_operations.annuler_operation(id_annulee, contexte["id_user"])

    caisse = service_caisses.lire_caisse(contexte["id_caisse"])["donnees"]
    assert caisse["Solde_Actuel"] == 500  # inchangé


def test_solde_stable_apres_comptabilisation(contexte):
    """Comptabiliser ne doit pas faire bouger le solde une seconde fois."""
    id_operation = _creer_depense(contexte, montant=100)
    service_operations.valider_operation(id_operation, contexte["id_manager"])
    solde_apres_validation = service_caisses.lire_caisse(contexte["id_caisse"])["donnees"]["Solde_Actuel"]

    service_operations.comptabiliser_operation(id_operation, contexte["id_manager"])
    solde_apres_comptabilisation = service_caisses.lire_caisse(contexte["id_caisse"])["donnees"]["Solde_Actuel"]

    assert solde_apres_validation == solde_apres_comptabilisation == 400


# --- Historique --------------------------------------------------------------------

def test_modification_trace_dans_historique(contexte, session_app):
    id_operation = _creer_depense(contexte, montant=100)
    service_operations.modifier_operation(id_operation, contexte["id_user"], Montant=120, Observation="Corrigé")

    lignes = session_app.query(HistoriqueCaisse).filter(HistoriqueCaisse.Id_Operation == id_operation).all()
    champs_modifies = {l.Champ_Modifie for l in lignes}
    assert champs_modifies == {"Montant", "Observation"}
    ligne_montant = next(l for l in lignes if l.Champ_Modifie == "Montant")
    # Montant est un NUMERIC(18,2) : stocké comme Decimal, donc "100.00" et non "100".
    assert float(ligne_montant.Ancienne_Valeur) == 100
    assert float(ligne_montant.Nouvelle_Valeur) == 120
