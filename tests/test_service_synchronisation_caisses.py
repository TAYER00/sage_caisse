"""
Tests du service de synchronisation des caisses depuis BIJOU (Phase 11).

Une fausse connexion Sage (FausseConnexionSage) remplace
ConnexionSageLectureSeule - ces tests ne touchent jamais la vraie base
BIJOU (comme le reste de la suite : seule une vérification manuelle,
documentée dans 00_analyse/11_PHASE1_ANALYSE_SYNC_BIJOU.md, a été faite
contre la vraie base).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_caisses, service_synchronisation_caisses, service_utilisateurs


class FausseConnexionSage:
    """Simule ConnexionSageLectureSeule.executer_lecture() sans toucher BIJOU."""

    def __init__(self, lignes):
        self._lignes = lignes

    def executer_lecture(self, requete, parametres=None):
        return self._lignes


CAISSES_SAGE_EXEMPLE = [
    {"CA_No": 1, "CA_Intitule": "Caisse 1 Bijou SA", "DE_No": 1, "Societe": "Bijou SA"},
    {"CA_No": 2, "CA_Intitule": "Caisse 2 Bijou SA", "DE_No": 1, "Societe": "Bijou SA"},
    {"CA_No": 3, "CA_Intitule": "Caisse 1 Annexe Bijou", "DE_No": 1, "Societe": "Bijou SA"},
]


@pytest.fixture
def contexte(session_app):
    id_manager = service_utilisateurs.creer_utilisateur("manager", "x", "Manager Test", "MANAGER")["id"]
    id_user = service_utilisateurs.creer_utilisateur("employe", "x", "Employe Test")["id"]
    return {"id_manager": id_manager, "id_user": id_user}


def test_synchronisation_cree_les_caisses_inconnues(contexte):
    connexion_sage = FausseConnexionSage(CAISSES_SAGE_EXEMPLE)
    resultat = service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, contexte["id_manager"])
    assert resultat["succes"] is True
    assert resultat["creees"] == 3
    assert resultat["mises_a_jour"] == 0

    caisses = service_caisses.lister_caisses()["resultats"]
    assert len(caisses) == 3
    numeros = {c["Numero_Caisse_Sage"] for c in caisses}
    assert numeros == {1, 2, 3}


def test_synchronisation_est_idempotente(contexte):
    """Rejouer la synchronisation ne doit jamais créer de doublon (clé = Numero_Caisse_Sage)."""
    connexion_sage = FausseConnexionSage(CAISSES_SAGE_EXEMPLE)
    service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, contexte["id_manager"])
    resultat = service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, contexte["id_manager"])

    assert resultat["creees"] == 0
    assert resultat["mises_a_jour"] == 3
    assert len(service_caisses.lister_caisses()["resultats"]) == 3  # toujours 3, pas 6


def test_resynchronisation_ne_touche_jamais_au_nom_ni_au_solde(contexte):
    """
    Nom_Caisse devient une donnee propre a l'application dès sa création -
    une resynchronisation met a jour Societe, mais ne doit JAMAIS réécraser
    un nom déjà choisi (même si CA_Intitule change côté Sage), ni toucher
    au solde. Bug réel trouvé en testant contre la vraie base (le nom
    choisi "Caisse Principale Siège" avait été écrasé par "Caisse 1 Bijou
    SA") - corrigé avant la fin de la Phase 11.
    """
    connexion_sage = FausseConnexionSage(CAISSES_SAGE_EXEMPLE)
    service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, contexte["id_manager"])

    from connexion.connexion_app import obtenir_session
    from modeles.caisse import Caisse

    caisse = next(c for c in service_caisses.lister_caisses()["resultats"] if c["Numero_Caisse_Sage"] == 1)
    nom_choisi = "Caisse Principale Siège (nom choisi par l'application)"
    session = obtenir_session()
    session.get(Caisse, caisse["Id_Caisse"]).Nom_Caisse = nom_choisi
    session.commit()
    session.close()
    service_caisses.recalculer_solde(caisse["Id_Caisse"])  # solde a 0, normal (pas d'operation)

    # Le libelle Sage change (ex. renomme dans Sage) et la societe aussi -> societe doit se refleter, pas le nom.
    connexion_modifiee = FausseConnexionSage([
        {"CA_No": 1, "CA_Intitule": "Caisse 1 Bijou SA RENOMMEE COTE SAGE", "DE_No": 1, "Societe": "Bijou SA Modifiee"},
    ])
    service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_modifiee, contexte["id_manager"])

    caisse_relue = service_caisses.lire_caisse(caisse["Id_Caisse"])["donnees"]
    assert caisse_relue["Nom_Caisse"] == nom_choisi  # jamais ecrase
    assert caisse_relue["Societe"] == "Bijou SA Modifiee"  # donnee de reference, mise a jour
    assert caisse_relue["Solde_Actuel"] == 0  # inchange, jamais touche par la synchro


def test_synchronisation_ne_touche_pas_une_caisse_sans_lien_sage(contexte):
    id_caisse_locale = service_caisses.creer_caisse("CA-LOCALE", "Caisse 100% applicative", "Bijou SA")["id"]
    connexion_sage = FausseConnexionSage(CAISSES_SAGE_EXEMPLE)
    service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, contexte["id_manager"])

    caisses = service_caisses.lister_caisses()["resultats"]
    assert len(caisses) == 4  # 1 locale + 3 synchronisees
    locale = next(c for c in caisses if c["Id_Caisse"] == id_caisse_locale)
    assert locale["Numero_Caisse_Sage"] is None


def test_synchronisation_refusee_pour_un_user(contexte):
    connexion_sage = FausseConnexionSage(CAISSES_SAGE_EXEMPLE)
    with pytest.raises(ErreurValidation, match="droits"):
        service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, contexte["id_user"])
