"""
Connexion SQLAlchemy à la base applicative SAGE_CAISSE_APP (lecture et
écriture - seule base où ce projet écrit).

Contrairement à connexion_sage_lecture.py (pyodbc brut, lecture seule sur
Sage), cette base est la nôtre : on utilise SQLAlchemy (recommandé par le
prompt) pour profiter de la gestion de session, des transactions, et de la
correspondance avec les modèles (voir modeles.py).
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config.configuration import ConfigurationAppSage
from gestion_erreurs.exceptions import ErreurConnexion, message_sql_lisible

_moteur = None
_SessionLocale = None


def obtenir_moteur():
    """
    Objectif : créer (une seule fois) le moteur SQLAlchemy connecté à
    SAGE_CAISSE_APP.

    Retour : l'objet Engine SQLAlchemy.

    Erreurs possibles : ErreurConnexion si la configuration est invalide
    (le moteur lui-même ne se connecte qu'au premier usage réel).
    """
    global _moteur
    if _moteur is None:
        try:
            _moteur = create_engine(ConfigurationAppSage.url_sqlalchemy(), pool_pre_ping=True)
        except ValueError as erreur:
            raise ErreurConnexion(f"[ERREUR] {erreur}") from erreur
    return _moteur


def obtenir_session():
    """
    Objectif : fournir une nouvelle session SQLAlchemy sur SAGE_CAISSE_APP.

    Retour : une Session SQLAlchemy - à fermer par l'appelant
    (de préférence avec un bloc "with" ou un try/finally).

    Exemple :
        session = obtenir_session()
        try:
            ...
        finally:
            session.close()
    """
    global _SessionLocale
    if _SessionLocale is None:
        _SessionLocale = sessionmaker(bind=obtenir_moteur())
    return _SessionLocale()


def tester_connexion() -> bool:
    """
    Objectif : vérifier que la connexion à SAGE_CAISSE_APP est possible.

    Retour : True si une requête minimale réussit.

    Erreurs possibles : ErreurConnexion si la connexion échoue (base
    inexistante, identifiants invalides, serveur injoignable...).

    Exemple :
        tester_connexion()
    """
    try:
        with obtenir_moteur().connect() as connexion:
            connexion.execute(text("SELECT 1"))
        return True
    except Exception as erreur:
        raise ErreurConnexion(
            f"[ERREUR] Connexion à la base applicative impossible : "
            f"{message_sql_lisible(erreur)}"
        ) from erreur
