import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_parametres


def test_creer_et_lister_parametre(session_app):
    resultat = service_parametres.creer_parametre("MOTIF", "DEPLACEMENT", "Frais de déplacement")
    assert resultat["succes"] is True

    parametres = service_parametres.lister_parametres("MOTIF")["resultats"]
    assert len(parametres) == 1
    assert parametres[0]["Libelle"] == "Frais de déplacement"
    assert parametres[0]["Actif"] is True


def test_creer_parametre_refuse_doublon_categorie_code(session_app):
    service_parametres.creer_parametre("MOTIF", "DEPLACEMENT", "Frais de déplacement")
    with pytest.raises(ErreurValidation):
        service_parametres.creer_parametre("MOTIF", "DEPLACEMENT", "Autre libellé")


def test_desactiver_parametre_ne_le_supprime_pas(session_app):
    id_parametre = service_parametres.creer_parametre("MOTIF", "REPAS", "Frais de repas")["id"]

    resultat = service_parametres.desactiver_parametre(id_parametre)
    assert resultat["succes"] is True

    actifs = service_parametres.lister_parametres("MOTIF", actifs_seulement=True)["resultats"]
    assert actifs == []

    tous = service_parametres.lister_parametres("MOTIF", actifs_seulement=False)["resultats"]
    assert len(tous) == 1  # toujours présent, juste désactivé


def test_desactiver_parametre_inexistant_leve_erreur(session_app):
    with pytest.raises(ErreurValidation):
        service_parametres.desactiver_parametre(999)
