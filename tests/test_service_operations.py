import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestion_erreurs.exceptions import ErreurValidation
from services import service_caisses, service_operations, service_utilisateurs


@pytest.fixture
def contexte(session_app):
    """Un utilisateur et une caisse réels, prêts pour créer des opérations."""
    id_utilisateur = service_utilisateurs.creer_utilisateur("test", "MotDePasse123!", "Testeur")["id"]
    id_caisse = service_caisses.creer_caisse("CA-1", "Caisse Test", "Bijou SA", solde_initial=500)["id"]
    return {"id_utilisateur": id_utilisateur, "id_caisse": id_caisse}


def test_creer_operation_alimentation_impose_sens_entree(contexte):
    resultat = service_operations.creer_operation(
        "ALIMENTATION", contexte["id_caisse"], datetime.now(), 100, contexte["id_utilisateur"],
    )
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(resultat["id"])["donnees"]
    assert operation["Sens_Solde"] == "ENTREE"
    assert operation["Statut"] == "BROUILLON"
    assert operation["Reference"].startswith("OP-")


def test_creer_operation_depense_impose_sens_sortie(contexte):
    resultat = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45.90, contexte["id_utilisateur"], projet="Déplacement Lyon",
    )
    operation = service_operations.lire_operation(resultat["id"])["donnees"]
    assert operation["Sens_Solde"] == "SORTIE"
    assert operation["Projet"] == "Déplacement Lyon"


def test_creer_operation_remboursement_exige_sens_explicite(contexte):
    """Règle du prompt : ne jamais déduire automatiquement le sens d'un remboursement."""
    with pytest.raises(ErreurValidation):
        service_operations.creer_operation(
            "REMBOURSEMENT", contexte["id_caisse"], datetime.now(), 30, contexte["id_utilisateur"],
        )  # sens_solde non fourni -> doit échouer


def test_creer_operation_remboursement_avec_sens_explicite_fonctionne(contexte):
    resultat = service_operations.creer_operation(
        "REMBOURSEMENT", contexte["id_caisse"], datetime.now(), 30, contexte["id_utilisateur"], sens_solde="SORTIE",
    )
    operation = service_operations.lire_operation(resultat["id"])["donnees"]
    assert operation["Sens_Solde"] == "SORTIE"


def test_creer_operation_refuse_montant_negatif_ou_nul(contexte):
    with pytest.raises(ErreurValidation):
        service_operations.creer_operation("DEPENSE", contexte["id_caisse"], datetime.now(), 0, contexte["id_utilisateur"])
    with pytest.raises(ErreurValidation):
        service_operations.creer_operation("DEPENSE", contexte["id_caisse"], datetime.now(), -10, contexte["id_utilisateur"])


def test_creer_operation_refuse_caisse_inexistante(contexte):
    with pytest.raises(ErreurValidation):
        service_operations.creer_operation("DEPENSE", 999, datetime.now(), 10, contexte["id_utilisateur"])


def test_reference_automatique_incrementale(contexte):
    r1 = service_operations.creer_operation("DEPENSE", contexte["id_caisse"], datetime.now(), 10, contexte["id_utilisateur"])
    r2 = service_operations.creer_operation("DEPENSE", contexte["id_caisse"], datetime.now(), 20, contexte["id_utilisateur"])
    assert r1["reference"] != r2["reference"]
    assert r1["reference"].endswith("000001")
    assert r2["reference"].endswith("000002")


def test_modifier_operation_en_brouillon_fonctionne(contexte):
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]

    resultat = service_operations.modifier_operation(
        id_operation, contexte["id_utilisateur"], Montant=52.30, Observation="Taxi + pourboire"
    )
    assert resultat["succes"] is True

    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Montant"] == 52.30
    assert operation["Observation"] == "Taxi + pourboire"


def test_modifier_operation_tous_les_champs_en_brouillon(contexte):
    """prmopt_3.txt : tous les champs doivent être modifiables tant que BROUILLON."""
    autre_caisse = service_caisses.creer_caisse("CA-2", "Autre Caisse", "Bijou SA", solde_initial=0)["id"]
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]

    resultat = service_operations.modifier_operation(
        id_operation, contexte["id_utilisateur"],
        Id_Caisse=autre_caisse, Societe="Autre Société", Beneficiaire="C00123",
        Responsable=contexte["id_utilisateur"], Compte_Financier="5310", Compte_Analytique="PROJ-A",
        Devise="MAD",
    )
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Id_Caisse"] == autre_caisse
    assert operation["Societe"] == "Autre Société"
    assert operation["Devise"] == "MAD"


def test_modifier_operation_refuse_caisse_inexistante(contexte):
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    with pytest.raises(ErreurValidation):
        service_operations.modifier_operation(id_operation, contexte["id_utilisateur"], Id_Caisse=999)


def test_modifier_operation_changement_type_impose_le_sens(contexte):
    """Passer de DEPENSE à ALIMENTATION doit recalculer Sens_Solde automatiquement (même règle qu'à la création)."""
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    service_operations.modifier_operation(id_operation, contexte["id_utilisateur"], Type_Operation="ALIMENTATION")
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Type_Operation"] == "ALIMENTATION"
    assert operation["Sens_Solde"] == "ENTREE"


def test_modifier_operation_devenir_remboursement_exige_sens_explicite(contexte):
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    with pytest.raises(ErreurValidation):
        service_operations.modifier_operation(id_operation, contexte["id_utilisateur"], Type_Operation="REMBOURSEMENT")

    resultat = service_operations.modifier_operation(
        id_operation, contexte["id_utilisateur"], Type_Operation="REMBOURSEMENT", Sens_Solde="ENTREE"
    )
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Sens_Solde"] == "ENTREE"


def test_modifier_operation_annulee_fonctionne(contexte):
    """Phase 10 : BROUILLON et ANNULE se comportent de façon identique - une ANNULE reste modifiable."""
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    service_operations.annuler_operation(id_operation, contexte["id_utilisateur"])

    resultat = service_operations.modifier_operation(id_operation, contexte["id_utilisateur"], Montant=60)
    assert resultat["succes"] is True
    operation = service_operations.lire_operation(id_operation)["donnees"]
    assert operation["Montant"] == 60
    assert operation["Statut"] == "ANNULE"  # la modification seule ne change pas le statut


def test_modifier_operation_validee_est_bloquee(contexte, session_app):
    from modeles.operation import OperationCaisse

    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    # Simule une opération déjà validée en modifiant directement le statut
    # (évite de dépendre ici du workflow réel, testé séparément).
    operation = session_app.get(OperationCaisse, id_operation)
    operation.Statut = "VALIDE"
    session_app.commit()

    with pytest.raises(ErreurValidation):
        service_operations.modifier_operation(id_operation, contexte["id_utilisateur"], Montant=99)


def test_supprimer_operation_brouillon_par_manager_fonctionne(contexte):
    """prmopt_3.txt : la suppression directe est réservée EXCLUSIVEMENT aux MANAGER."""
    id_manager = service_utilisateurs.creer_utilisateur("manager_del", "x", "Manager Suppression", "MANAGER")["id"]
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    resultat = service_operations.supprimer_operation(id_operation, id_manager, confirmer=True)
    assert resultat["succes"] is True
    with pytest.raises(ErreurValidation):
        service_operations.lire_operation(id_operation)


def test_supprimer_operation_refuse_si_pas_manager_meme_createur(contexte):
    """Le créateur USER ne peut plus supprimer, même sa propre opération en brouillon."""
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    with pytest.raises(ErreurValidation, match="droits"):
        service_operations.supprimer_operation(id_operation, contexte["id_utilisateur"], confirmer=True)


def test_supprimer_operation_annulee_par_manager_fonctionne(contexte):
    id_manager = service_utilisateurs.creer_utilisateur("manager_del2", "x", "Manager Suppression 2", "MANAGER")["id"]
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    service_operations.annuler_operation(id_operation, contexte["id_utilisateur"])
    resultat = service_operations.supprimer_operation(id_operation, id_manager, confirmer=True)
    assert resultat["succes"] is True


def test_supprimer_operation_validee_est_refusee_meme_par_manager(contexte):
    id_manager = service_utilisateurs.creer_utilisateur("manager_del3", "x", "Manager Suppression 3", "MANAGER")["id"]
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    service_operations.valider_operation(id_operation, id_manager)
    with pytest.raises(ErreurValidation):
        service_operations.supprimer_operation(id_operation, id_manager, confirmer=True)


def test_supprimer_operation_refuse_sans_confirmation(contexte):
    id_operation = service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 45, contexte["id_utilisateur"]
    )["id"]
    with pytest.raises(ErreurValidation):
        service_operations.supprimer_operation(id_operation, contexte["id_utilisateur"], confirmer=False)


def test_lister_operations_filtre_par_projet_caisse_responsable(contexte):
    service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 10, contexte["id_utilisateur"],
        projet="Lyon", responsable=contexte["id_utilisateur"],
    )
    service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 20, contexte["id_utilisateur"], projet="Paris",
    )

    par_projet = service_operations.lister_operations(projet="Lyon")["resultats"]
    assert len(par_projet) == 1
    assert par_projet[0]["Projet"] == "Lyon"

    par_caisse = service_operations.lister_operations(id_caisse=contexte["id_caisse"])["resultats"]
    assert len(par_caisse) == 2

    par_responsable = service_operations.lister_operations(responsable=contexte["id_utilisateur"])["resultats"]
    assert len(par_responsable) == 1


def test_lister_operations_recherche_texte_libre(contexte):
    service_operations.creer_operation(
        "DEPENSE", contexte["id_caisse"], datetime.now(), 15, contexte["id_utilisateur"], observation="Achat de timbres",
    )
    resultats = service_operations.lister_operations(recherche_texte="timbres")["resultats"]
    assert len(resultats) == 1
