import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_utilisateurs
from services.securite import hacher_mot_de_passe, verifier_mot_de_passe


def test_hachage_mot_de_passe_ne_stocke_jamais_le_mot_de_passe_en_clair():
    hache = hacher_mot_de_passe("MotDePasse123!")
    assert "MotDePasse123!" not in hache
    assert verifier_mot_de_passe("MotDePasse123!", hache) is True
    assert verifier_mot_de_passe("MauvaisMotDePasse", hache) is False


def test_creer_utilisateur(session_app):
    resultat = service_utilisateurs.creer_utilisateur("dburon", "MotDePasse123!", "Dorine Buron", "MANAGER")
    assert resultat["succes"] is True
    assert "[SUCCES]" in resultat["message"]

    utilisateurs = service_utilisateurs.lister_utilisateurs()["resultats"]
    assert len(utilisateurs) == 1
    assert utilisateurs[0]["Login"] == "dburon"
    assert utilisateurs[0]["Role"] == "MANAGER"


def test_creer_utilisateur_refuse_login_vide(session_app):
    with pytest.raises(ErreurValidation):
        service_utilisateurs.creer_utilisateur("", "MotDePasse123!", "Sans Login")


def test_creer_utilisateur_refuse_role_invalide(session_app):
    with pytest.raises(ErreurValidation):
        service_utilisateurs.creer_utilisateur("test", "MotDePasse123!", "Test", role="SUPERADMIN")


def test_creer_utilisateur_refuse_login_deja_pris(session_app):
    service_utilisateurs.creer_utilisateur("dburon", "MotDePasse123!", "Dorine Buron")
    with pytest.raises(ErreurValidation):
        service_utilisateurs.creer_utilisateur("dburon", "AutreMotDePasse", "Autre Personne")


def test_authentifier_avec_bon_mot_de_passe(session_app):
    service_utilisateurs.creer_utilisateur("dburon", "MotDePasse123!", "Dorine Buron", "MANAGER")
    resultat = service_utilisateurs.authentifier("dburon", "MotDePasse123!")
    assert resultat["succes"] is True
    assert resultat["utilisateur"]["Login"] == "dburon"
    assert resultat["utilisateur"]["Role"] == "MANAGER"
    assert "Mot_De_Passe_Hash" not in resultat["utilisateur"]  # jamais renvoye au client


def test_authentifier_avec_mauvais_mot_de_passe(session_app):
    service_utilisateurs.creer_utilisateur("dburon", "MotDePasse123!", "Dorine Buron")
    with pytest.raises(ErreurValidation, match="Identifiants incorrects"):
        service_utilisateurs.authentifier("dburon", "MauvaisMotDePasse")


def test_authentifier_login_inexistant_meme_message_erreur(session_app):
    """Ne doit jamais reveler si le login existe ou non (bonne pratique de securite)."""
    with pytest.raises(ErreurValidation, match="Identifiants incorrects"):
        service_utilisateurs.authentifier("login_qui_n_existe_pas", "peu_importe")


def test_manager_peut_reinitialiser_le_mot_de_passe_dun_autre(session_app):
    id_manager = service_utilisateurs.creer_utilisateur("manager", "x", "Manager Test", "MANAGER")["id"]
    id_user = service_utilisateurs.creer_utilisateur("employe", "AncienMotDePasse", "Employe Test")["id"]

    resultat = service_utilisateurs.reinitialiser_mot_de_passe(id_user, "NouveauMotDePasse123!", id_manager)
    assert resultat["succes"] is True

    # L'ancien mot de passe ne fonctionne plus, le nouveau fonctionne.
    with pytest.raises(ErreurValidation):
        service_utilisateurs.authentifier("employe", "AncienMotDePasse")
    confirmation = service_utilisateurs.authentifier("employe", "NouveauMotDePasse123!")
    assert confirmation["succes"] is True


def test_user_ne_peut_pas_reinitialiser_le_mot_de_passe_dun_autre(session_app):
    id_user1 = service_utilisateurs.creer_utilisateur("employe1", "x", "Employe 1")["id"]
    id_user2 = service_utilisateurs.creer_utilisateur("employe2", "x", "Employe 2")["id"]

    with pytest.raises(ErreurValidation, match="droits"):
        service_utilisateurs.reinitialiser_mot_de_passe(id_user2, "Nouveau123!", id_user1)


def test_utilisateur_peut_reinitialiser_son_propre_mot_de_passe(session_app):
    id_user = service_utilisateurs.creer_utilisateur("employe", "AncienMotDePasse", "Employe Test")["id"]
    resultat = service_utilisateurs.reinitialiser_mot_de_passe(id_user, "NouveauMotDePasse123!", id_user)
    assert resultat["succes"] is True
