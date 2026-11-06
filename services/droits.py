"""
Vérifications de droits communes au workflow (Phase 5) - voir
00_analyse/05_PHASE5_WORKFLOW.md section 1 pour le tableau des règles.

Message d'erreur repris mot pour mot de l'exemple du prompt :
"Vous n'avez pas les droits nécessaires."
"""

from config.configuration import mode_lecture_seule_actif
from gestion_erreurs.exceptions import ErreurValidation
from modeles.utilisateur import Utilisateur


def verifier_ecriture_autorisee() -> None:
    """
    Objectif : refuser toute écriture sur la base applicative quand le
    mode lecture seule est actif (voir config/configuration.py -
    definir_mode_lecture_seule()/mode_lecture_seule_actif(), même
    mécanisme que sage_to_shopify). À appeler en tout premier, avant
    toute autre validation, dans chaque fonction qui écrit
    (créer/modifier/supprimer/valider/annuler/comptabiliser...).

    Erreurs possibles : ErreurValidation si le mode lecture seule est actif.

    Exemple :
        verifier_ecriture_autorisee()
    """
    if mode_lecture_seule_actif():
        raise ErreurValidation(
            "[VALIDATION] Mode lecture seule actif : aucune création, modification, "
            "suppression ou action de workflow n'est autorisée sur la base applicative."
        )


def obtenir_utilisateur(session, id_utilisateur: int) -> Utilisateur:
    """
    Objectif : charger un utilisateur, en levant une erreur claire s'il
    n'existe pas (plutôt qu'une exception technique plus loin).

    Exemple :
        obtenir_utilisateur(session, 1)
    """
    utilisateur = session.get(Utilisateur, id_utilisateur)
    if utilisateur is None:
        raise ErreurValidation(f"[VALIDATION] L'utilisateur {id_utilisateur} n'existe pas.")
    return utilisateur


def exiger_role(utilisateur: Utilisateur, roles_autorises: tuple[str, ...]) -> None:
    """
    Objectif : vérifier que l'utilisateur a l'un des rôles autorisés.

    Erreurs possibles : ErreurValidation si le rôle ne convient pas.

    Exemple :
        exiger_role(utilisateur, ("MANAGER",))
    """
    if utilisateur.Role not in roles_autorises:
        raise ErreurValidation("[VALIDATION] Vous n'avez pas les droits nécessaires.")


def exiger_createur_ou_manager(utilisateur: Utilisateur, id_createur: int) -> None:
    """
    Objectif : vérifier que l'utilisateur est soit le créateur de
    l'opération, soit un MANAGER.

    Erreurs possibles : ErreurValidation sinon.

    Exemple :
        exiger_createur_ou_manager(utilisateur, operation.Cree_Par)
    """
    if utilisateur.Id_Utilisateur != id_createur and utilisateur.Role != "MANAGER":
        raise ErreurValidation("[VALIDATION] Vous n'avez pas les droits nécessaires.")
