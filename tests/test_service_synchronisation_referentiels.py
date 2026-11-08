"""
Tests du service de synchronisation des référentiels Sage (tiers,
collaborateurs) - Phase 12. Une fausse connexion Sage remplace
ConnexionSageLectureSeule, aucun test automatisé ne touche la vraie base
BIJOU (seule une vérification manuelle, documentée dans 00_analyse/, a
été faite contre la vraie base).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_synchronisation_referentiels, service_utilisateurs


class FausseConnexionSage:
    """Simule executer_lecture() - retourne des tiers ou des collaborateurs selon la requête."""

    def __init__(self, tiers, collaborateurs):
        self._tiers = tiers
        self._collaborateurs = collaborateurs

    def executer_lecture(self, requete, parametres=None):
        return self._tiers if "F_COMPTET" in requete else self._collaborateurs


TIERS_EXEMPLE = [
    {"CT_Num": "C00001", "CT_Intitule": "Client Alpha", "CT_Type": 0},
    {"CT_Num": "F00001", "CT_Intitule": "Fournisseur Beta", "CT_Type": 1},
]

COLLABORATEURS_EXEMPLE = [
    {"CO_No": 4, "CO_Nom": "ECLAT", "CO_Prenom": "Dorine", "CO_Caissier": 1},
    {"CO_No": 8, "CO_Nom": "HAMAND", "CO_Prenom": "Eddy", "CO_Caissier": 1},
]


@pytest.fixture
def contexte(session_app):
    id_manager = service_utilisateurs.creer_utilisateur("manager", "x", "Manager Test", "MANAGER")["id"]
    id_user = service_utilisateurs.creer_utilisateur("employe", "x", "Employe Test")["id"]
    return {"id_manager": id_manager, "id_user": id_user}


def test_synchronisation_cree_tiers_et_collaborateurs(contexte):
    connexion_sage = FausseConnexionSage(TIERS_EXEMPLE, COLLABORATEURS_EXEMPLE)
    resultat = service_synchronisation_referentiels.synchroniser_referentiels_depuis_sage(connexion_sage, contexte["id_manager"])
    assert resultat["succes"] is True
    assert resultat["tiers"] == 2
    assert resultat["collaborateurs"] == 2

    tiers = service_synchronisation_referentiels.lister_tiers()["resultats"]
    assert {t["CT_Num"] for t in tiers} == {"C00001", "F00001"}

    collaborateurs = service_synchronisation_referentiels.lister_collaborateurs()["resultats"]
    noms = {c["Nom_Complet"] for c in collaborateurs}
    assert noms == {"ECLAT Dorine", "HAMAND Eddy"}


def test_synchronisation_est_idempotente_et_reflete_les_changements(contexte):
    connexion_sage = FausseConnexionSage(TIERS_EXEMPLE, COLLABORATEURS_EXEMPLE)
    service_synchronisation_referentiels.synchroniser_referentiels_depuis_sage(connexion_sage, contexte["id_manager"])

    connexion_modifiee = FausseConnexionSage(
        [{"CT_Num": "C00001", "CT_Intitule": "Client Alpha RENOMME", "CT_Type": 0}],
        COLLABORATEURS_EXEMPLE,
    )
    service_synchronisation_referentiels.synchroniser_referentiels_depuis_sage(connexion_modifiee, contexte["id_manager"])

    tiers = service_synchronisation_referentiels.lister_tiers()["resultats"]
    # F00001 n'etait plus dans le flux Sage lors du 2e appel, mais la synchro ne supprime
    # jamais automatiquement (prudence) - il reste donc present, inchange.
    assert len(tiers) == 2
    alpha = next(t for t in tiers if t["CT_Num"] == "C00001")
    assert alpha["Intitule"] == "Client Alpha RENOMME"


def test_synchronisation_referentiels_refusee_pour_un_user(contexte):
    connexion_sage = FausseConnexionSage(TIERS_EXEMPLE, COLLABORATEURS_EXEMPLE)
    with pytest.raises(ErreurValidation, match="droits"):
        service_synchronisation_referentiels.synchroniser_referentiels_depuis_sage(connexion_sage, contexte["id_user"])
