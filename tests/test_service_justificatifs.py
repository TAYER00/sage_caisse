"""
Tests du service Justificatifs (Phase 7). Le dossier de stockage réel du
projet n'est jamais utilisé dans les tests - il est redirigé vers un
dossier temporaire (voir fixture `dossier_stockage_temp`).
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_caisses, service_justificatifs, service_operations, service_utilisateurs


@pytest.fixture
def dossier_stockage_temp(tmp_path, monkeypatch):
    monkeypatch.setattr(service_justificatifs, "DOSSIER_STOCKAGE", tmp_path)
    return tmp_path


@pytest.fixture
def contexte(session_app):
    id_utilisateur = service_utilisateurs.creer_utilisateur("test", "x", "Testeur", "MANAGER")["id"]
    id_caisse = service_caisses.creer_caisse("CA-1", "Caisse Test", "Bijou SA")["id"]
    id_operation = service_operations.creer_operation("DEPENSE", id_caisse, datetime.now(), 50, id_utilisateur)["id"]
    return {"id_utilisateur": id_utilisateur, "id_operation": id_operation}


def test_ajouter_et_lister_justificatif(contexte, dossier_stockage_temp):
    resultat = service_justificatifs.ajouter_justificatif(
        contexte["id_operation"], "facture.pdf", b"%PDF-1.4 contenu de test", contexte["id_utilisateur"]
    )
    assert resultat["succes"] is True

    justificatifs = service_justificatifs.lister_justificatifs(contexte["id_operation"])["resultats"]
    assert len(justificatifs) == 1
    assert justificatifs[0]["Nom_Fichier"] == "facture.pdf"
    assert justificatifs[0]["Type_Fichier"] == "PDF"


def test_fichier_reellement_ecrit_sur_disque(contexte, dossier_stockage_temp):
    service_justificatifs.ajouter_justificatif(contexte["id_operation"], "photo.jpg", b"contenu binaire", contexte["id_utilisateur"])
    fichiers = list(dossier_stockage_temp.rglob("*.jpg"))
    assert len(fichiers) == 1
    assert fichiers[0].read_bytes() == b"contenu binaire"


def test_refuse_extension_non_autorisee(contexte, dossier_stockage_temp):
    with pytest.raises(ErreurValidation, match="non autorisée"):
        service_justificatifs.ajouter_justificatif(contexte["id_operation"], "virus.exe", b"x", contexte["id_utilisateur"])


def test_refuse_fichier_vide(contexte, dossier_stockage_temp):
    with pytest.raises(ErreurValidation, match="vide"):
        service_justificatifs.ajouter_justificatif(contexte["id_operation"], "vide.pdf", b"", contexte["id_utilisateur"])


def test_refuse_fichier_trop_volumineux(contexte, dossier_stockage_temp):
    contenu_trop_gros = b"x" * (service_justificatifs.TAILLE_MAX_OCTETS + 1)
    with pytest.raises(ErreurValidation, match="taille maximale"):
        service_justificatifs.ajouter_justificatif(contexte["id_operation"], "gros.pdf", contenu_trop_gros, contexte["id_utilisateur"])


def test_telecharger_justificatif(contexte, dossier_stockage_temp):
    id_justificatif = service_justificatifs.ajouter_justificatif(
        contexte["id_operation"], "facture.pdf", b"contenu", contexte["id_utilisateur"]
    )["id"]
    chemin, nom = service_justificatifs.lire_fichier_justificatif(id_justificatif)
    assert nom == "facture.pdf"
    assert chemin.read_bytes() == b"contenu"


def test_supprimer_justificatif_en_brouillon(contexte, dossier_stockage_temp):
    id_justificatif = service_justificatifs.ajouter_justificatif(
        contexte["id_operation"], "facture.pdf", b"contenu", contexte["id_utilisateur"]
    )["id"]
    resultat = service_justificatifs.supprimer_justificatif(id_justificatif, contexte["id_utilisateur"])
    assert resultat["succes"] is True
    assert service_justificatifs.lister_justificatifs(contexte["id_operation"])["resultats"] == []


def test_supprimer_justificatif_apres_validation_est_refuse(contexte, dossier_stockage_temp):
    id_justificatif = service_justificatifs.ajouter_justificatif(
        contexte["id_operation"], "facture.pdf", b"contenu", contexte["id_utilisateur"]
    )["id"]
    service_operations.valider_operation(contexte["id_operation"], contexte["id_utilisateur"])
    with pytest.raises(ErreurValidation, match="avant la validation"):
        service_justificatifs.supprimer_justificatif(id_justificatif, contexte["id_utilisateur"])


def test_ajouter_justificatif_sur_operation_annulee_est_refuse(contexte, dossier_stockage_temp):
    service_operations.annuler_operation(contexte["id_operation"], contexte["id_utilisateur"])
    with pytest.raises(ErreurValidation, match="ANNULE"):
        service_justificatifs.ajouter_justificatif(contexte["id_operation"], "facture.pdf", b"contenu", contexte["id_utilisateur"])
