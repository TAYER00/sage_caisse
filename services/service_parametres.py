"""
Service métier "Paramètres de caisse" (listes dynamiques, ex. motifs).

Règle du prompt : jamais de suppression physique d'une valeur déjà
utilisée - seulement une désactivation (Actif = False).
"""

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import (
    ErreurSQL,
    ErreurValidation,
    message_sql_lisible,
    message_succes,
)
from modeles.operation import OperationCaisse
from modeles.parametre import ParametreCaisse
from services import droits


def creer_parametre(categorie: str, code: str, libelle: str) -> dict:
    """
    Objectif : créer une nouvelle valeur de liste dynamique (ex. un motif).

    Parametres :
        categorie (str) : ex. "MOTIF".
        code (str) : code court unique dans sa catégorie.
        libelle (str) : libellé affiché.

    Retour : dict {"succes": True, "message": str, "id": int}.

    Erreurs possibles : ErreurValidation (champ manquant, doublon), ErreurSQL.

    Exemple :
        creer_parametre("MOTIF", "DEPLACEMENT", "Frais de déplacement")
    """
    droits.verifier_ecriture_autorisee()
    if not categorie or not categorie.strip():
        raise ErreurValidation("[VALIDATION] La catégorie est obligatoire.")
    if not code or not code.strip():
        raise ErreurValidation("[VALIDATION] Le code est obligatoire.")
    if not libelle or not libelle.strip():
        raise ErreurValidation("[VALIDATION] Le libellé est obligatoire.")

    session = obtenir_session()
    try:
        parametre = ParametreCaisse(Categorie=categorie.strip().upper(), Code=code.strip().upper(), Libelle=libelle.strip())
        session.add(parametre)
        session.commit()
        return {
            "succes": True,
            "message": message_succes(f"Paramètre '{libelle}' créé avec succès."),
            "id": parametre.Id_Parametre,
        }
    except IntegrityError as erreur:
        session.rollback()
        raise ErreurValidation(f"[VALIDATION] Le code '{code}' existe déjà pour la catégorie '{categorie}'.") from erreur
    except SQLAlchemyError as erreur:
        session.rollback()
        raise ErreurSQL(f"[ERREUR] Création du paramètre impossible : {message_sql_lisible(erreur)}") from erreur
    finally:
        session.close()


def lister_parametres(categorie: str = None, actifs_seulement: bool = True) -> dict:
    """
    Objectif : lister les valeurs d'une catégorie de liste dynamique.

    Exemple :
        lister_parametres("MOTIF")
    """
    session = obtenir_session()
    try:
        requete = session.query(ParametreCaisse)
        if categorie:
            requete = requete.filter(ParametreCaisse.Categorie == categorie.strip().upper())
        if actifs_seulement:
            requete = requete.filter(ParametreCaisse.Actif == True)  # noqa: E712 - .is_(True) genere "IS 1", invalide sur SQL Server
        parametres = requete.order_by(ParametreCaisse.Libelle).all()
        resultats = [
            {"Id_Parametre": p.Id_Parametre, "Categorie": p.Categorie, "Code": p.Code, "Libelle": p.Libelle, "Actif": p.Actif}
            for p in parametres
        ]
        return {
            "succes": True,
            "message": message_succes(f"{len(resultats)} paramètre(s) trouvé(s)."),
            "resultats": resultats,
        }
    finally:
        session.close()


def desactiver_parametre(id_parametre: int) -> dict:
    """
    Objectif : désactiver une valeur de liste dynamique SANS la supprimer
    physiquement (règle du prompt - une valeur déjà utilisée doit rester
    consultable dans l'historique).

    Retour : dict {"succes": True, "message": str}.

    Erreurs possibles : ErreurValidation si le paramètre n'existe pas.

    Exemple :
        desactiver_parametre(3)
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        parametre = session.get(ParametreCaisse, id_parametre)
        if parametre is None:
            raise ErreurValidation(f"[VALIDATION] Le paramètre {id_parametre} n'existe pas.")
        parametre.Actif = False
        session.commit()
        return {"succes": True, "message": message_succes(f"Paramètre '{parametre.Libelle}' désactivé avec succès.")}
    finally:
        session.close()


def parametre_est_utilise(id_parametre: int) -> bool:
    """
    Objectif : savoir si un paramètre est déjà référencé par au moins une
    opération - utile pour refuser toute suppression physique (règle du
    prompt), même si cette fonction n'est appelée par aucune route de
    suppression (il n'y en a volontairement pas).

    Exemple :
        parametre_est_utilise(3)
    """
    session = obtenir_session()
    try:
        return session.query(OperationCaisse).filter(OperationCaisse.Id_Motif == id_parametre).first() is not None
    finally:
        session.close()
