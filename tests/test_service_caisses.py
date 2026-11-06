import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_caisses


def test_creer_et_lire_caisse(session_app):
    resultat = service_caisses.creer_caisse("CA-BIJOU-1", "Caisse Bijou SA", "Bijou SA", solde_initial=100, numero_caisse_sage=1)
    assert resultat["succes"] is True

    caisse = service_caisses.lire_caisse(resultat["id"])["donnees"]
    assert caisse["Code_Caisse"] == "CA-BIJOU-1"
    assert caisse["Solde_Initial"] == 100
    assert caisse["Solde_Actuel"] == 100  # au départ, identique au solde initial
    assert caisse["Numero_Caisse_Sage"] == 1
    assert caisse["Statut"] == "ACTIF"


def test_creer_caisse_refuse_code_vide(session_app):
    with pytest.raises(ErreurValidation):
        service_caisses.creer_caisse("", "Caisse sans code", "Bijou SA")


def test_creer_caisse_refuse_doublon_code(session_app):
    service_caisses.creer_caisse("CA-1", "Caisse 1", "Bijou SA")
    with pytest.raises(ErreurValidation):
        service_caisses.creer_caisse("CA-1", "Autre caisse", "Bijou SA")


def test_lire_caisse_inexistante_leve_erreur(session_app):
    with pytest.raises(ErreurValidation):
        service_caisses.lire_caisse(999)


def test_lister_caisses(session_app):
    service_caisses.creer_caisse("CA-1", "Caisse 1", "Bijou SA")
    service_caisses.creer_caisse("CA-2", "Caisse 2", "Bijou SA")
    caisses = service_caisses.lister_caisses()["resultats"]
    assert len(caisses) == 2
