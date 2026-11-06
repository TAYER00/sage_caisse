"""
Tests de la connexion SQL en lecture seule à la base Sage BIJOU (Phase 1).

Les 5 tests demandés explicitement par le prompt :
    1. Connexion réussie
    2. Connexion refusée
    3. Table inexistante
    4. Requête incorrecte
    5. Lecture de données
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.configuration import ConfigurationSageLectureSeule
from connexion.connexion_sage_lecture import ConnexionSageLectureSeule
from gestion_erreurs.exceptions import ErreurConnexion


def test_1_connexion_reussie():
    """Test 1 : la connexion à la base Sage BIJOU doit pouvoir s'ouvrir."""
    connexion = ConnexionSageLectureSeule()
    assert connexion.tester_connexion() is True
    assert connexion.est_ouverte is True


def test_2_connexion_refusee_mauvais_mot_de_passe(monkeypatch):
    """Test 2 : un mauvais mot de passe doit lever ErreurConnexion, pas planter."""
    monkeypatch.setattr(ConfigurationSageLectureSeule, "MOT_DE_PASSE", "mot_de_passe_volontairement_faux")
    connexion = ConnexionSageLectureSeule()
    with pytest.raises(ErreurConnexion):
        connexion.tester_connexion()


def test_3_table_inexistante():
    """Test 3 : lire une table qui n'existe pas doit lever ErreurConnexion (erreur SQL propre)."""
    connexion = ConnexionSageLectureSeule()
    connexion.tester_connexion()
    with pytest.raises(ErreurConnexion):
        connexion.executer_lecture("SELECT * FROM TABLE_QUI_N_EXISTE_PAS_DU_TOUT")


def test_4_requete_incorrecte():
    """Test 4 : une requête SQL syntaxiquement invalide doit lever ErreurConnexion."""
    connexion = ConnexionSageLectureSeule()
    connexion.tester_connexion()
    with pytest.raises(ErreurConnexion):
        connexion.executer_lecture("SELECT TOP 5 FROM FROM F_CREGLEMENT")


def test_5_lecture_de_donnees():
    """Test 5 : une lecture valide doit renvoyer une liste exploitable (même vide)."""
    connexion = ConnexionSageLectureSeule()
    connexion.tester_connexion()
    lignes = connexion.executer_lecture("SELECT TOP 5 RG_No, RG_Montant FROM F_CREGLEMENT")
    assert isinstance(lignes, list)  # F_CREGLEMENT est vide dans BIJOU : liste vide attendue, pas une erreur


def test_executer_lecture_refuse_ecriture():
    """Garde-fou supplémentaire : aucune écriture possible, même par erreur."""
    connexion = ConnexionSageLectureSeule()
    with pytest.raises(ValueError):
        connexion.executer_lecture("DELETE FROM F_CREGLEMENT")
