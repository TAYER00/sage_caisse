"""
Configuration centralisée du projet sage_caisse.

Lit les paramètres depuis le fichier .env (non versionné - voir
.env.example pour le modèle).

Deux bases SQL Server distinctes, comme dans sage_to_shopify :
    - ConfigurationSageLectureSeule : Sage BIJOU, lecture seule uniquement.
    - ConfigurationAppSage : base applicative SAGE_CAISSE_APP (créée en
      Phase 3), lecture + écriture - seule base où ce projet écrit.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class ConfigurationSageLectureSeule:
    """
    Paramètres de connexion directe à la base SQL Server de Sage 100
    (BIJOU), strictement en LECTURE SEULE (compte db_datareader).

    Même compte BIJOU_READONLY déjà créé et validé dans sage_Conex_CRUD et
    sage_to_shopify, sur ce même serveur.
    """

    SERVEUR = os.getenv("SQL_SERVER", "")
    BASE = os.getenv("SQL_DATABASE_SAGE", "BIJOU")
    UTILISATEUR = os.getenv("SQL_READONLY_USERNAME", "")
    MOT_DE_PASSE = os.getenv("SQL_READONLY_PASSWORD", "")

    @classmethod
    def valider(cls):
        """Lève ValueError si un paramètre de connexion obligatoire manque."""
        requis = [cls.SERVEUR, cls.BASE, cls.UTILISATEUR, cls.MOT_DE_PASSE]
        if not all(requis):
            raise ValueError(
                "Configuration SQL Sage (lecture seule) incomplète. "
                "Vérifiez SQL_SERVER / SQL_DATABASE_SAGE / "
                "SQL_READONLY_USERNAME / SQL_READONLY_PASSWORD dans le "
                "fichier .env."
            )


class ConfigurationAppSage:
    """
    Paramètres de connexion à la base applicative SAGE_CAISSE_APP (lecture
    + écriture - voir 00_analyse/04_SCHEMA_SAGE_CAISSE.sql pour le schéma
    réel, déjà créé et vérifié).
    """

    SERVEUR = os.getenv("SQL_SERVER", "")
    BASE = os.getenv("SQL_DATABASE_APP", "SAGE_CAISSE_APP")
    UTILISATEUR = os.getenv("SQL_APP_USERNAME", "")
    MOT_DE_PASSE = os.getenv("SQL_APP_PASSWORD", "")

    @classmethod
    def valider(cls):
        """Lève ValueError si un paramètre de connexion obligatoire manque."""
        requis = [cls.SERVEUR, cls.BASE, cls.UTILISATEUR, cls.MOT_DE_PASSE]
        if not all(requis):
            raise ValueError(
                "Configuration SQL de la base applicative incomplète. "
                "Vérifiez SQL_SERVER / SQL_DATABASE_APP / SQL_APP_USERNAME "
                "/ SQL_APP_PASSWORD dans le fichier .env."
            )

    @classmethod
    def url_sqlalchemy(cls) -> str:
        """Construit l'URL de connexion SQLAlchemy (pyodbc) pour cette base."""
        cls.valider()
        from urllib.parse import quote_plus

        chaine_odbc = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={cls.SERVEUR};DATABASE={cls.BASE};"
            f"UID={cls.UTILISATEUR};PWD={cls.MOT_DE_PASSE};"
            "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=10;"
        )
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(chaine_odbc)}"


# --- Mode lecture seule flexible (identique à sage_to_shopify) -------------
#
# Ne concerne que les écritures sur SAGE_CAISSE_APP. Sage reste de toute
# facon inaccessible en ecriture (ConnexionSageLectureSeule n'expose aucune
# methode d'ecriture), quel que soit ce reglage.
_dernier_choix_utilisateur = None


def definir_mode_lecture_seule(actif: bool) -> None:
    """Change le mode lecture seule EN MEMOIRE, sans toucher .env ni redemarrer."""
    global _dernier_choix_utilisateur
    _dernier_choix_utilisateur = actif


def mode_lecture_seule_actif() -> bool:
    """
    Indique si le mode lecture seule est actif pour la base applicative.
    Priorite au choix fait en memoire via definir_mode_lecture_seule().
    """
    if _dernier_choix_utilisateur is not None:
        return _dernier_choix_utilisateur
    return os.getenv("MODE_LECTURE_SEULE", "true").strip().lower() == "true"


# --- Durcissement production (Phase 8) --------------------------------------

ENVIRONNEMENT = os.getenv("ENVIRONNEMENT", "developpement").strip().lower()

ORIGINES_AUTORISEES = [
    origine.strip()
    for origine in os.getenv("ORIGINES_AUTORISEES", "http://127.0.0.1:5500,http://localhost:5500").split(",")
    if origine.strip()
]
