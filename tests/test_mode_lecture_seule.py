"""
Test du garde-fou MODE_LECTURE_SEULE (Phase 1 promis, réellement câblé en
Phase 6) : aucune écriture sur la base applicative n'est possible quand
le mode lecture seule est actif, quel que soit le service appelé.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.configuration import definir_mode_lecture_seule
from gestion_erreurs.exceptions import ErreurValidation
from services import service_caisses, service_operations, service_parametres, service_utilisateurs


def test_creer_caisse_bloquee_en_mode_lecture_seule(session_app):
    definir_mode_lecture_seule(True)
    with pytest.raises(ErreurValidation, match="lecture seule"):
        service_caisses.creer_caisse("CA-1", "Caisse 1", "Bijou SA")


def test_creer_utilisateur_bloquee_en_mode_lecture_seule(session_app):
    definir_mode_lecture_seule(True)
    with pytest.raises(ErreurValidation, match="lecture seule"):
        service_utilisateurs.creer_utilisateur("test", "x", "Test")


def test_creer_parametre_bloquee_en_mode_lecture_seule(session_app):
    definir_mode_lecture_seule(True)
    with pytest.raises(ErreurValidation, match="lecture seule"):
        service_parametres.creer_parametre("MOTIF", "X", "Libellé")


def test_creer_operation_bloquee_en_mode_lecture_seule(session_app):
    definir_mode_lecture_seule(False)  # setup : créer un contexte valide d'abord
    id_utilisateur = service_utilisateurs.creer_utilisateur("test", "x", "Test")["id"]
    id_caisse = service_caisses.creer_caisse("CA-1", "Caisse 1", "Bijou SA")["id"]

    definir_mode_lecture_seule(True)  # puis on active le mode lecture seule pour le vrai test
    with pytest.raises(ErreurValidation, match="lecture seule"):
        service_operations.creer_operation("DEPENSE", id_caisse, datetime.now(), 10, id_utilisateur)


def test_lire_et_lister_restent_autorises_en_mode_lecture_seule(session_app):
    definir_mode_lecture_seule(False)
    service_caisses.creer_caisse("CA-1", "Caisse 1", "Bijou SA")

    definir_mode_lecture_seule(True)
    service_caisses.lister_caisses()  # ne doit lever aucune erreur
