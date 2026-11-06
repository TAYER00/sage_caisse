"""
Exceptions dédiées au projet sage_caisse et aides pour les messages en
français ([SUCCES] / [ERREUR] / [VALIDATION]).

Repris à l'identique du pattern déjà écrit et validé dans
sage_to_shopify/gestion_erreurs/exceptions.py (même serveur, même type de
connexion SQL Server).
"""

import re


class ErreurSageCaisse(Exception):
    """Classe de base pour toutes les erreurs de ce projet."""


class ErreurConnexion(ErreurSageCaisse):
    """La connexion SQL Server (Sage, ou plus tard la base applicative) a échoué."""


class ErreurValidation(ErreurSageCaisse):
    """Un champ obligatoire manque, une valeur est invalide, ou une règle métier est violée."""


class ErreurSQL(ErreurSageCaisse):
    """
    Encapsule une erreur pyodbc brute, pour éviter de propager directement
    le tuple technique peu lisible renvoyé par le driver ODBC.
    """


def message_succes(texte: str) -> str:
    """Formate un message de succès standard : '[SUCCES] <texte>'."""
    return f"[SUCCES] {texte}"


def message_erreur(texte: str) -> str:
    """Formate un message d'erreur standard : '[ERREUR] <texte>'."""
    return f"[ERREUR] {texte}"


def message_validation(texte: str) -> str:
    """Formate un message de validation standard : '[VALIDATION] <texte>'."""
    return f"[VALIDATION] {texte}"


# Préfixe technique ajouté par le driver ODBC avant le vrai message SQL
# Server, du genre : "[42000] [Microsoft][ODBC Driver 18 for SQL Server]
# [SQL Server]Invalid object name 'FOO'. (208) (SQLExecDirectW)"
_PREFIXE_ODBC = re.compile(r"^(\[[^\]]*\]\s*)+")
_SUFFIXE_CODE_SQL = re.compile(r"\s*\(\d+\)\s*(\(SQL\w+\))?\s*$")


def message_sql_lisible(erreur: Exception) -> str:
    """
    Objectif : extraire, d'une exception pyodbc brute, le seul texte utile
    envoyé par SQL Server - sans le préfixe technique du driver ODBC ni le
    code d'erreur numérique final.

    Parametres : erreur (Exception) - l'exception capturée (pyodbc.Error
    ou autre).

    Retour : le message SQL Server lisible si le format est reconnu,
    sinon str(erreur) tel quel.

    Exemple :
        message_sql_lisible(erreur)
        -> "Invalid object name 'F_TABLEQUINEXISTEPAS'."
    """
    texte = str(erreur)
    # SQLAlchemy encapsule l'erreur pyodbc d'origine dans .orig.
    source = getattr(erreur, "orig", erreur)
    args = getattr(source, "args", None)
    if args and len(args) >= 2 and isinstance(args[1], str):
        texte = args[1]

    nettoye = _PREFIXE_ODBC.sub("", texte).strip()
    nettoye = _SUFFIXE_CODE_SQL.sub("", nettoye).strip()
    return nettoye or texte
