"""
Service métier "Utilisateur" - CRUD de base (Phase 4) + authentification
réelle (Phase 7, remplace le sélecteur "Agir en tant que" provisoire de la
Phase 6).
"""

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import (
    ErreurSQL,
    ErreurValidation,
    message_sql_lisible,
    message_succes,
)
from modeles.utilisateur import Utilisateur
from services import droits
from services.securite import hacher_mot_de_passe, verifier_mot_de_passe

ROLES_VALIDES = ("USER", "MANAGER")


def creer_utilisateur(login: str, mot_de_passe: str, nom_complet: str, role: str = "USER") -> dict:
    """
    Objectif : créer un nouvel utilisateur applicatif.

    Parametres :
        login (str) : identifiant de connexion, doit être unique.
        mot_de_passe (str) : mot de passe en clair - sera haché, jamais stocké tel quel.
        nom_complet (str) : nom affiché.
        role (str) : "USER" ou "MANAGER" (défaut "USER").

    Retour : dict {"succes": True, "message": str, "id": int}.

    Validations : login/mot_de_passe/nom_complet non vides, rôle valide,
    login pas déjà utilisé.

    Erreurs possibles : ErreurValidation, ErreurSQL.

    Exemple :
        creer_utilisateur("dburon", "MotDePasse123!", "Dorine Buron", "MANAGER")
    """
    droits.verifier_ecriture_autorisee()
    if not login or not login.strip():
        raise ErreurValidation("[VALIDATION] Le login est obligatoire.")
    if not mot_de_passe or not mot_de_passe.strip():
        raise ErreurValidation("[VALIDATION] Le mot de passe est obligatoire.")
    if not nom_complet or not nom_complet.strip():
        raise ErreurValidation("[VALIDATION] Le nom complet est obligatoire.")
    if role not in ROLES_VALIDES:
        raise ErreurValidation(f"[VALIDATION] Rôle invalide : {role}. Attendu : {ROLES_VALIDES}.")

    session = obtenir_session()
    try:
        utilisateur = Utilisateur(
            Login=login.strip(),
            Mot_De_Passe_Hash=hacher_mot_de_passe(mot_de_passe),
            Nom_Complet=nom_complet.strip(),
            Role=role,
        )
        session.add(utilisateur)
        session.commit()
        return {
            "succes": True,
            "message": message_succes(f"Utilisateur '{login}' créé avec succès."),
            "id": utilisateur.Id_Utilisateur,
        }
    except IntegrityError as erreur:
        session.rollback()
        raise ErreurValidation(f"[VALIDATION] Le login '{login}' est déjà utilisé.") from erreur
    except SQLAlchemyError as erreur:
        session.rollback()
        raise ErreurSQL(f"[ERREUR] Création de l'utilisateur impossible : {message_sql_lisible(erreur)}") from erreur
    finally:
        session.close()


def authentifier(login: str, mot_de_passe: str) -> dict:
    """
    Objectif : vérifier un couple login/mot de passe et retourner
    l'identité de l'utilisateur si correct - remplace le sélecteur
    "Agir en tant que" provisoire de la Phase 6 par une vraie
    authentification (règle du prompt : "Authentification : login et mot
    de passe").

    Parametres :
        login (str), mot_de_passe (str) : en clair, jamais loggués.

    Retour : dict {"succes": True, "message": str, "utilisateur": {...}}.

    Validations : login/mot de passe non vides, utilisateur existant et
    actif, mot de passe correct.

    Erreurs possibles : ErreurValidation - **volontairement le même
    message** que le login soit inconnu ou le mot de passe faux, pour ne
    jamais révéler si un login existe (bonne pratique de sécurité).

    Exemple :
        authentifier("dburon", "MotDePasse123!")
    """
    if not login or not login.strip():
        raise ErreurValidation("[VALIDATION] Le login est obligatoire.")
    if not mot_de_passe:
        raise ErreurValidation("[VALIDATION] Le mot de passe est obligatoire.")

    session = obtenir_session()
    try:
        utilisateur = session.query(Utilisateur).filter(Utilisateur.Login == login.strip()).first()
        mot_de_passe_valide = utilisateur is not None and utilisateur.Actif and verifier_mot_de_passe(mot_de_passe, utilisateur.Mot_De_Passe_Hash)
        if not mot_de_passe_valide:
            raise ErreurValidation("[VALIDATION] Identifiants incorrects.")

        return {
            "succes": True,
            "message": message_succes(f"Bienvenue, {utilisateur.Nom_Complet}."),
            "utilisateur": {
                "Id_Utilisateur": utilisateur.Id_Utilisateur, "Login": utilisateur.Login,
                "Nom_Complet": utilisateur.Nom_Complet, "Role": utilisateur.Role,
            },
        }
    finally:
        session.close()


def reinitialiser_mot_de_passe(id_utilisateur: int, nouveau_mot_de_passe: str, utilisateur_id: int) -> dict:
    """
    Objectif : réinitialiser le mot de passe d'un utilisateur - utile
    notamment pour les comptes créés directement en base (hors
    application), avec un mot de passe dans un format non géré par
    `services/securite.py` (ex. hash bcrypt saisi à la main).

    Parametres :
        id_utilisateur (int) : compte dont le mot de passe est réinitialisé.
        nouveau_mot_de_passe (str) : en clair, sera haché, jamais stocké tel quel.
        utilisateur_id (int) : utilisateur qui déclenche l'action - doit
            être MANAGER (action sensible), ou le compte lui-même.

    Retour : dict {"succes": True, "message": str}.

    Erreurs possibles : ErreurValidation (compte introuvable, mot de passe
    vide, droits insuffisants).

    Exemple :
        reinitialiser_mot_de_passe(1, "NouveauMotDePasse123!", utilisateur_id=4)
    """
    droits.verifier_ecriture_autorisee()
    if not nouveau_mot_de_passe or not nouveau_mot_de_passe.strip():
        raise ErreurValidation("[VALIDATION] Le nouveau mot de passe est obligatoire.")

    session = obtenir_session()
    try:
        acteur = droits.obtenir_utilisateur(session, utilisateur_id)
        if acteur.Role != "MANAGER" and acteur.Id_Utilisateur != id_utilisateur:
            raise ErreurValidation("[VALIDATION] Vous n'avez pas les droits nécessaires.")

        utilisateur = session.get(Utilisateur, id_utilisateur)
        if utilisateur is None:
            raise ErreurValidation(f"[VALIDATION] L'utilisateur {id_utilisateur} n'existe pas.")

        utilisateur.Mot_De_Passe_Hash = hacher_mot_de_passe(nouveau_mot_de_passe)
        session.commit()

        # Relecture de contrôle : le nouveau mot de passe doit réellement fonctionner.
        confirmation = session.get(Utilisateur, id_utilisateur)
        if not verifier_mot_de_passe(nouveau_mot_de_passe, confirmation.Mot_De_Passe_Hash):
            raise ErreurSQL("[ERREUR] La réinitialisation n'a pas pu être confirmée par relecture.")

        return {"succes": True, "message": message_succes(f"Mot de passe de '{confirmation.Login}' réinitialisé avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def lister_utilisateurs(actifs_seulement: bool = True) -> dict:
    """
    Objectif : lister les utilisateurs applicatifs.

    Retour : dict {"succes": True, "message": str, "resultats": list[dict]}.

    Exemple :
        lister_utilisateurs()
    """
    session = obtenir_session()
    try:
        requete = session.query(Utilisateur)
        if actifs_seulement:
            requete = requete.filter(Utilisateur.Actif == True)  # noqa: E712 - .is_(True) genere "IS 1", invalide sur SQL Server
        utilisateurs = requete.order_by(Utilisateur.Login).all()
        resultats = [
            {
                "Id_Utilisateur": u.Id_Utilisateur,
                "Login": u.Login,
                "Nom_Complet": u.Nom_Complet,
                "Role": u.Role,
                "Actif": u.Actif,
            }
            for u in utilisateurs
        ]
        return {
            "succes": True,
            "message": message_succes(f"{len(resultats)} utilisateur(s) trouvé(s)."),
            "resultats": resultats,
        }
    finally:
        session.close()
