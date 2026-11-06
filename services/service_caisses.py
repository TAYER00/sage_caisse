"""
Service métier "Caisse" - CRUD de base (Phase 4) + calcul réel du solde
(Phase 5).
"""

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import (
    ErreurSQL,
    ErreurValidation,
    message_sql_lisible,
    message_succes,
)
from modeles.caisse import Caisse
from modeles.operation import OperationCaisse
from services import droits

STATUTS_VALIDES = ("ACTIF", "INACTIF")
STATUTS_COMPTANT_POUR_LE_SOLDE = ("VALIDE", "COMPTABILISE")


def creer_caisse(
    code_caisse: str,
    nom_caisse: str,
    societe: str,
    solde_initial: float = 0,
    numero_caisse_sage: int = None,
    compte_financier: str = None,
    responsable_caisse: int = None,
    devise: str = "EUR",
    connexion_sage=None,
) -> dict:
    """
    Objectif : créer une nouvelle caisse applicative.

    Parametres :
        code_caisse, nom_caisse, societe : obligatoires.
        solde_initial (float) : défaut 0.
        numero_caisse_sage / compte_financier / responsable_caisse :
            références Sage optionnelles (F_CAISSE.CA_No,
            F_COMPTEG.CG_Num, F_COLLABORATEUR.CO_No).
        connexion_sage : si fournie (ConnexionSageLectureSeule déjà
            testée), les références Sage données sont vérifiées
            réellement dans Sage avant d'être acceptées - sinon, elles
            sont acceptées sans vérification (utile pour les tests).

    Retour : dict {"succes": True, "message": str, "id": int}.

    Erreurs possibles : ErreurValidation (champ manquant, doublon de
    code, référence Sage introuvable), ErreurSQL.

    Exemple :
        creer_caisse("CA-BIJOU-1", "Caisse Bijou SA", "Bijou SA", numero_caisse_sage=1)
    """
    droits.verifier_ecriture_autorisee()
    if not code_caisse or not code_caisse.strip():
        raise ErreurValidation("[VALIDATION] Le code caisse est obligatoire.")
    if not nom_caisse or not nom_caisse.strip():
        raise ErreurValidation("[VALIDATION] Le nom de la caisse est obligatoire.")
    if not societe or not societe.strip():
        raise ErreurValidation("[VALIDATION] La société est obligatoire.")

    if connexion_sage is not None:
        from objets_metier import lecture_sage

        if numero_caisse_sage is not None and lecture_sage.lire_caisse_sage(connexion_sage, numero_caisse_sage) is None:
            raise ErreurValidation(f"[VALIDATION] La caisse Sage {numero_caisse_sage} n'existe pas.")
        if compte_financier and lecture_sage.lire_compte_general_sage(connexion_sage, compte_financier) is None:
            raise ErreurValidation(f"[VALIDATION] Le compte général Sage '{compte_financier}' n'existe pas.")
        if responsable_caisse is not None and lecture_sage.lire_collaborateur_sage(connexion_sage, responsable_caisse) is None:
            raise ErreurValidation(f"[VALIDATION] Le collaborateur Sage {responsable_caisse} n'existe pas.")

    session = obtenir_session()
    try:
        caisse = Caisse(
            Code_Caisse=code_caisse.strip(),
            Nom_Caisse=nom_caisse.strip(),
            Societe=societe.strip(),
            Numero_Caisse_Sage=numero_caisse_sage,
            Compte_Financier=compte_financier,
            Responsable_Caisse=responsable_caisse,
            Devise=devise,
            Solde_Initial=solde_initial,
            Solde_Actuel=solde_initial,
        )
        session.add(caisse)
        session.commit()
        return {
            "succes": True,
            "message": message_succes(f"Caisse '{nom_caisse}' créée avec succès."),
            "id": caisse.Id_Caisse,
        }
    except IntegrityError as erreur:
        session.rollback()
        raise ErreurValidation(f"[VALIDATION] Le code caisse '{code_caisse}' existe déjà.") from erreur
    except SQLAlchemyError as erreur:
        session.rollback()
        raise ErreurSQL(f"[ERREUR] Création de la caisse impossible : {message_sql_lisible(erreur)}") from erreur
    finally:
        session.close()


def lire_caisse(id_caisse: int) -> dict:
    """
    Objectif : lire une caisse par son identifiant.

    Erreurs possibles : ErreurValidation si la caisse n'existe pas.

    Exemple :
        lire_caisse(1)
    """
    session = obtenir_session()
    try:
        caisse = session.get(Caisse, id_caisse)
        if caisse is None:
            raise ErreurValidation(f"[VALIDATION] La caisse {id_caisse} n'existe pas.")
        return {
            "succes": True,
            "message": message_succes(f"Caisse '{caisse.Nom_Caisse}' lue avec succès."),
            "donnees": _vers_dict(caisse),
        }
    finally:
        session.close()


def lister_caisses(actives_seulement: bool = False) -> dict:
    """
    Objectif : lister les caisses.

    Exemple :
        lister_caisses()
    """
    session = obtenir_session()
    try:
        requete = session.query(Caisse)
        if actives_seulement:
            requete = requete.filter(Caisse.Statut == "ACTIF")
        caisses = requete.order_by(Caisse.Nom_Caisse).all()
        resultats = [_vers_dict(c) for c in caisses]
        return {
            "succes": True,
            "message": message_succes(f"{len(resultats)} caisse(s) trouvée(s)."),
            "resultats": resultats,
        }
    finally:
        session.close()


def recalculer_solde(id_caisse: int, session=None) -> dict:
    """
    Objectif : recalculer le solde réel d'une caisse à partir de ses
    opérations (règle du prompt : "Ne jamais modifier directement un
    solde sans mouvement correspondant") - recalcul complet, pas
    incrémental, pour éviter tout risque de double-comptage ou d'oubli.

    Formule (voir 00_analyse/05_PHASE5_WORKFLOW.md section 2) :
        Solde_Actuel = Solde_Initial
            + SUM(Montant) des opérations VALIDE/COMPTABILISE, Sens_Solde=ENTREE
            - SUM(Montant) des opérations VALIDE/COMPTABILISE, Sens_Solde=SORTIE

    Parametres :
        id_caisse (int) : caisse à recalculer.
        session : session SQLAlchemy existante à réutiliser (pour rester
            dans la même transaction qu'une action de workflow) - sinon
            une nouvelle session est ouverte et fermée ici.

    Retour : dict {"succes": True, "message": str, "solde": float}.

    Erreurs possibles : ErreurValidation si la caisse n'existe pas.

    Exemple :
        recalculer_solde(1)
    """
    droits.verifier_ecriture_autorisee()
    session_locale = session is None
    session = session or obtenir_session()
    try:
        caisse = session.get(Caisse, id_caisse)
        if caisse is None:
            raise ErreurValidation(f"[VALIDATION] La caisse {id_caisse} n'existe pas.")

        def _somme(sens: str):
            return session.query(func.sum(OperationCaisse.Montant)).filter(
                OperationCaisse.Id_Caisse == id_caisse,
                OperationCaisse.Statut.in_(STATUTS_COMPTANT_POUR_LE_SOLDE),
                OperationCaisse.Sens_Solde == sens,
            ).scalar() or 0

        caisse.Solde_Actuel = caisse.Solde_Initial + _somme("ENTREE") - _somme("SORTIE")
        if session_locale:
            session.commit()
        else:
            session.flush()

        return {
            "succes": True,
            "message": message_succes(f"Solde de la caisse '{caisse.Nom_Caisse}' recalculé avec succès."),
            "solde": float(caisse.Solde_Actuel),
        }
    finally:
        if session_locale:
            session.close()


def _vers_dict(caisse: Caisse) -> dict:
    return {
        "Id_Caisse": caisse.Id_Caisse,
        "Code_Caisse": caisse.Code_Caisse,
        "Nom_Caisse": caisse.Nom_Caisse,
        "Societe": caisse.Societe,
        "Numero_Caisse_Sage": caisse.Numero_Caisse_Sage,
        "Compte_Financier": caisse.Compte_Financier,
        "Responsable_Caisse": caisse.Responsable_Caisse,
        "Devise": caisse.Devise,
        "Solde_Initial": float(caisse.Solde_Initial),
        "Solde_Actuel": float(caisse.Solde_Actuel),
        "Statut": caisse.Statut,
    }
