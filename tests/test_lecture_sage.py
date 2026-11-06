"""
Tests de lecture de structure et d'échantillon (Phase 1) :
    - Lire la structure de F_CREGLEMENT
    - Afficher les premiers enregistrements (F_CREGLEMENT et F_CAISSE)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from connexion.connexion_sage_lecture import ConnexionSageLectureSeule
from objets_metier import lecture_sage


@pytest.fixture
def connexion():
    c = ConnexionSageLectureSeule()
    c.tester_connexion()
    return c


def test_structure_f_creglement_a_60_colonnes_reelles(connexion):
    """
    Ne jamais supposer le nombre de champs sans vérifier - déjà constaté
    dans docs/analyse_detaillee_f_creglement.md : 60 colonnes réelles.
    """
    nb = lecture_sage.compter_colonnes(connexion, "F_CREGLEMENT")
    assert nb == 60

    structure = lecture_sage.lire_structure_table(connexion, "F_CREGLEMENT")
    assert len(structure) == 60
    assert structure[0]["COLUMN_NAME"] == "RG_No"


def test_apercu_reglements_fonctionne_meme_sur_table_vide(connexion):
    """F_CREGLEMENT est vide dans BIJOU : la lecture doit réussir et renvoyer []."""
    lignes = lecture_sage.apercu_reglements(connexion, limite=5)
    assert isinstance(lignes, list)
    assert lignes == []


def test_apercu_caisses_renvoie_des_donnees_reelles(connexion):
    """F_CAISSE contient de vraies données (4 caisses) : premier test de lecture concrète réussi."""
    lignes = lecture_sage.apercu_caisses(connexion, limite=5)
    assert isinstance(lignes, list)
    assert len(lignes) > 0
    assert "CA_No" in lignes[0]
    assert "CA_Intitule" in lignes[0]
