"""
Connexion directe à la base SQL Server de Sage 100 (BIJOU), strictement en
LECTURE SEULE.

Règle absolue du projet sage_caisse (voir prompt.txt, section "CONNEXION
À SAGE 100 SQL SERVER") : ne jamais modifier F_CREGLEMENT ni aucune autre
table Sage. Cette classe n'expose volontairement AUCUNE méthode
d'écriture - executer_lecture() refuse toute requête qui ne commence pas
par SELECT, avant même de l'envoyer à SQL Server.

Pattern identique à sage_to_shopify/connexion/connexion_sage_lecture.py
(même serveur, même compte BIJOU_READONLY).
"""

import pyodbc

from config.configuration import ConfigurationSageLectureSeule
from gestion_erreurs.exceptions import ErreurConnexion, message_sql_lisible


class ConnexionSageLectureSeule:
    """Exécute des requêtes SELECT en lecture seule sur la base Sage BIJOU."""

    def __init__(self):
        ConfigurationSageLectureSeule.valider()
        self._chaine_connexion = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={ConfigurationSageLectureSeule.SERVEUR};"
            f"DATABASE={ConfigurationSageLectureSeule.BASE};"
            f"UID={ConfigurationSageLectureSeule.UTILISATEUR};"
            f"PWD={ConfigurationSageLectureSeule.MOT_DE_PASSE};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "Connection Timeout=10;"
        )
        self._ouverte = False

    @property
    def est_ouverte(self) -> bool:
        """Indique si tester_connexion() a déjà réussi au moins une fois."""
        return self._ouverte

    def tester_connexion(self) -> bool:
        """
        Objectif : vérifier que la connexion à la base Sage BIJOU est
        possible avec le compte en lecture seule.

        Parametres : aucun.

        Retour : True si la connexion s'ouvre et qu'une requête minimale
        ("SELECT 1") réussit.

        Erreurs possibles : ErreurConnexion si pyodbc ne parvient pas à
        ouvrir la connexion (serveur injoignable, identifiants invalides,
        droits insuffisants...).

        Exemple :
            ConnexionSageLectureSeule().tester_connexion()
        """
        try:
            with pyodbc.connect(self._chaine_connexion, timeout=10) as connexion:
                connexion.cursor().execute("SELECT 1")
            self._ouverte = True
            return True
        except pyodbc.Error as erreur:
            self._ouverte = False
            raise ErreurConnexion(
                f"[ERREUR] Connexion à la base Sage (lecture seule) "
                f"impossible : {message_sql_lisible(erreur)}"
            ) from erreur

    def executer_lecture(self, requete: str, parametres=None) -> list[dict]:
        """
        Objectif : exécuter une requête SELECT et retourner les résultats.

        Parametres :
            requete (str) : la requête SQL, qui doit commencer par SELECT.
            parametres (list, optionnel) : valeurs pour les "?" de la requête.

        Retour : une liste de dictionnaires (une entrée par ligne
        retournée, colonnes nommées).

        Validations : refuse toute requête qui ne commence pas par SELECT
        (lève ValueError) - cette classe ne doit jamais écrire sur Sage.

        Erreurs possibles : ErreurConnexion si la requête échoue côté SQL
        Server (table inexistante, requête incorrecte, droits
        insuffisants...).

        Exemple :
            connexion = ConnexionSageLectureSeule()
            connexion.executer_lecture(
                "SELECT TOP 5 RG_No, RG_Date, RG_Montant FROM F_CREGLEMENT"
            )
        """
        if not requete.strip().upper().startswith("SELECT"):
            raise ValueError(
                "[VALIDATION] Seules les requêtes SELECT sont autorisées "
                "par ConnexionSageLectureSeule - aucune écriture sur Sage "
                "n'est possible depuis ce projet."
            )

        try:
            with pyodbc.connect(self._chaine_connexion, timeout=10) as connexion:
                curseur = connexion.cursor()
                curseur.execute(requete, parametres or [])
                colonnes = [colonne[0] for colonne in curseur.description]
                lignes = [dict(zip(colonnes, ligne)) for ligne in curseur.fetchall()]
            self._ouverte = True
            return lignes
        except pyodbc.Error as erreur:
            raise ErreurConnexion(
                f"[ERREUR] Lecture impossible sur la base Sage : "
                f"{message_sql_lisible(erreur)}"
            ) from erreur
