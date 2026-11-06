"""Tests de l'export PDF (Phase 7)."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_caisses, service_operations, service_pdf, service_utilisateurs


@pytest.fixture
def contexte(session_app):
    id_manager = service_utilisateurs.creer_utilisateur("manager", "x", "Manager Test", "MANAGER")["id"]
    id_caisse = service_caisses.creer_caisse("CA-1", "Caisse Test", "Bijou SA")["id"]
    id_operation = service_operations.creer_operation("DEPENSE", id_caisse, datetime.now(), 50, id_manager)["id"]
    return {"id_manager": id_manager, "id_operation": id_operation}


def test_pdf_refuse_si_operation_en_brouillon(contexte):
    with pytest.raises(ErreurValidation, match="Validé"):
        service_pdf.generer_pdf_operation(contexte["id_operation"])


def test_pdf_genere_un_vrai_fichier_pdf_si_validee(contexte):
    service_operations.valider_operation(contexte["id_operation"], contexte["id_manager"])
    contenu = service_pdf.generer_pdf_operation(contexte["id_operation"])
    assert isinstance(contenu, bytes)
    assert contenu.startswith(b"%PDF-")  # signature reelle d'un fichier PDF
    assert len(contenu) > 500


def test_pdf_fonctionne_aussi_comptabilise(contexte):
    service_operations.valider_operation(contexte["id_operation"], contexte["id_manager"])
    service_operations.comptabiliser_operation(contexte["id_operation"], contexte["id_manager"])
    contenu = service_pdf.generer_pdf_operation(contexte["id_operation"])
    assert contenu.startswith(b"%PDF-")


def test_pdf_operation_inexistante(session_app):
    with pytest.raises(ErreurValidation):
        service_pdf.generer_pdf_operation(999)
