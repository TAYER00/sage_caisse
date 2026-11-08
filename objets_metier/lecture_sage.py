"""
Fonctions de LECTURE SEULE sur les tables Sage 100 utiles au projet
sage_caisse (F_CREGLEMENT en priorité, F_CAISSE pour le premier test sur
données réelles).

Phase 1 : uniquement des fonctions génériques de lecture de structure et
d'échantillon - l'analyse fonctionnelle détaillée champ par champ de
F_CREGLEMENT a déjà été produite dans docs/analyse_detaillee_f_creglement.md
(projet sage_to_shopify) et sera complétée pour le besoin "caisse" en
Phase 2.

Aucune méthode d'écriture ici : la connexion sous-jacente
(ConnexionSageLectureSeule) n'en expose aucune de toute façon.
"""

from gestion_erreurs.exceptions import ErreurValidation


def lire_structure_table(connexion, nom_table: str) -> list[dict]:
    """
    Objectif : lire la structure réelle (colonnes, types, nullabilité)
    d'une table Sage, sans jamais supposer sa composition.

    Parametres :
        connexion : une ConnexionSageLectureSeule déjà testée.
        nom_table (str) : nom de la table Sage (ex: "F_CREGLEMENT").

    Retour : liste de dict (une entrée par colonne, dans l'ordre réel) :
        ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
        NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE.

    Erreurs possibles : ErreurValidation si nom_table est vide.
        ErreurConnexion si la lecture échoue côté SQL Server.

    Exemple :
        lire_structure_table(connexion, "F_CREGLEMENT")
    """
    if not nom_table or not str(nom_table).strip():
        raise ErreurValidation("[VALIDATION] Le nom de la table est obligatoire.")

    return connexion.executer_lecture(
        "SELECT ORDINAL_POSITION, COLUMN_NAME, DATA_TYPE, "
        "CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE "
        "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? "
        "ORDER BY ORDINAL_POSITION",
        [nom_table],
    )


def compter_colonnes(connexion, nom_table: str) -> int:
    """
    Objectif : compter le nombre réel de colonnes d'une table Sage - pour
    ne jamais supposer un nombre de champs sans l'avoir vérifié (leçon de
    F_CREGLEMENT : 60 colonnes réelles, pas 62 supposées initialement).

    Exemple :
        compter_colonnes(connexion, "F_CREGLEMENT")  # -> 60
    """
    if not nom_table or not str(nom_table).strip():
        raise ErreurValidation("[VALIDATION] Le nom de la table est obligatoire.")

    resultat = connexion.executer_lecture(
        "SELECT COUNT(*) AS n FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ?",
        [nom_table],
    )
    return resultat[0]["n"]


def lister_premiers_enregistrements(connexion, nom_table: str, colonnes: list[str], limite: int = 5) -> list[dict]:
    """
    Objectif : afficher les premiers enregistrements d'une table Sage, sur
    un sous-ensemble de colonnes explicitement choisi (jamais "SELECT *" à
    l'aveugle sur une table métier).

    Parametres :
        connexion : une ConnexionSageLectureSeule déjà testée.
        nom_table (str) : nom de la table Sage.
        colonnes (list[str]) : noms des colonnes à afficher.
        limite (int) : nombre maximum de lignes (défaut 5).

    Retour : liste de dict (une entrée par ligne).

    Erreurs possibles : ErreurValidation si nom_table ou colonnes est vide.

    Exemple :
        lister_premiers_enregistrements(
            connexion, "F_CREGLEMENT",
            ["RG_No", "RG_Date", "RG_Montant", "RG_TypeReg"],
            limite=5,
        )
    """
    if not nom_table or not str(nom_table).strip():
        raise ErreurValidation("[VALIDATION] Le nom de la table est obligatoire.")
    if not colonnes:
        raise ErreurValidation("[VALIDATION] Au moins une colonne doit être précisée.")

    liste_colonnes = ", ".join(colonnes)
    return connexion.executer_lecture(
        f"SELECT TOP {int(limite)} {liste_colonnes} FROM {nom_table}"
    )


# --- Raccourcis pour les deux tables prioritaires de la Phase 1 ------------

COLONNES_REGLEMENT_APERCU = [
    "RG_No", "CT_NumPayeur", "RG_Date", "RG_Libelle", "RG_Montant",
    "RG_TypeReg", "RG_Valide", "RG_Compta", "CA_No", "CO_NoCaissier",
]

COLONNES_CAISSE_APERCU = [
    "CA_No", "CA_Intitule", "DE_No", "CO_No", "CT_Num",
]


def apercu_reglements(connexion, limite: int = 5) -> list[dict]:
    """Affiche les premiers enregistrements de F_CREGLEMENT (colonnes clés caisse)."""
    return lister_premiers_enregistrements(connexion, "F_CREGLEMENT", COLONNES_REGLEMENT_APERCU, limite)


def apercu_caisses(connexion, limite: int = 5) -> list[dict]:
    """Affiche les premiers enregistrements de F_CAISSE."""
    return lister_premiers_enregistrements(connexion, "F_CAISSE", COLONNES_CAISSE_APERCU, limite)


# --- Lectures ponctuelles, utilisées par services/ pour valider une        -
# --- référence Sage avant de l'accepter dans la base applicative          -

def lire_caisse_sage(connexion, ca_no: int) -> dict | None:
    """Lit une caisse Sage par CA_No, ou None si elle n'existe pas."""
    if ca_no is None:
        raise ErreurValidation("[VALIDATION] Le numéro de caisse Sage (CA_No) est obligatoire.")
    lignes = connexion.executer_lecture(
        f"SELECT {', '.join(COLONNES_CAISSE_APERCU)} FROM F_CAISSE WHERE CA_No = ?", [ca_no]
    )
    return lignes[0] if lignes else None


def lire_tiers_sage(connexion, ct_num: str) -> dict | None:
    """Lit un tiers Sage par CT_Num, ou None si il n'existe pas."""
    if not ct_num or not str(ct_num).strip():
        raise ErreurValidation("[VALIDATION] Le code tiers Sage (CT_Num) est obligatoire.")
    lignes = connexion.executer_lecture(
        "SELECT CT_Num, CT_Intitule, CT_Type FROM F_COMPTET WHERE CT_Num = ?", [ct_num]
    )
    return lignes[0] if lignes else None


def lire_compte_general_sage(connexion, cg_num: str) -> dict | None:
    """Lit un compte général Sage par CG_Num, ou None si il n'existe pas."""
    if not cg_num or not str(cg_num).strip():
        raise ErreurValidation("[VALIDATION] Le numéro de compte général Sage (CG_Num) est obligatoire.")
    lignes = connexion.executer_lecture(
        "SELECT CG_Num, CG_Intitule FROM F_COMPTEG WHERE CG_Num = ?", [cg_num]
    )
    return lignes[0] if lignes else None


def lister_caisses_sage(connexion) -> list[dict]:
    """
    Objectif : lire TOUTES les caisses réelles de Sage (F_CAISSE), jointes
    à F_DEPOT pour résoudre la société réelle (DE_No -> DE_Intitule) -
    utilisée par la synchronisation Phase 11 (voir
    00_analyse/11_PHASE1_ANALYSE_SYNC_BIJOU.md). Contrairement à
    lire_caisse_sage() (une seule caisse, par CA_No), cette fonction lit
    tout F_CAISSE en une fois, dans le même esprit que apercu_caisses()
    mais sans limite de lignes et avec le nom de société déjà résolu.

    Retour : liste de dict - une entrée par caisse Sage réelle :
        CA_No, CA_Intitule, DE_No, Societe (= F_DEPOT.DE_Intitule).

    Erreurs possibles : ErreurConnexion si la lecture échoue côté SQL Server.

    Exemple :
        lister_caisses_sage(connexion)
        # -> [{"CA_No": 1, "CA_Intitule": "Caisse 1 Bijou SA", "DE_No": 1, "Societe": "Bijou SA"}, ...]
    """
    return connexion.executer_lecture(
        "SELECT ca.CA_No, ca.CA_Intitule, ca.DE_No, de.DE_Intitule AS Societe "
        "FROM F_CAISSE ca JOIN F_DEPOT de ON de.DE_No = ca.DE_No "
        "ORDER BY ca.CA_No"
    )


def lister_tiers_sage(connexion) -> list[dict]:
    """
    Objectif : lire TOUS les tiers réels de Sage (F_COMPTET) - utilisée
    par la synchronisation Phase 12 (combobox "Bénéficiaire" du
    formulaire d'opération, remplace la saisie libre d'un code).

    Retour : liste de dict - CT_Num, CT_Intitule, CT_Type.

    Erreurs possibles : ErreurConnexion si la lecture échoue côté SQL Server.

    Exemple :
        lister_tiers_sage(connexion)
    """
    return connexion.executer_lecture(
        "SELECT CT_Num, CT_Intitule, CT_Type FROM F_COMPTET ORDER BY CT_Intitule"
    )


def lister_collaborateurs_sage(connexion) -> list[dict]:
    """
    Objectif : lire TOUS les collaborateurs réels de Sage
    (F_COLLABORATEUR) - utilisée par la synchronisation Phase 12
    (combobox "Responsable" du formulaire d'opération).

    Retour : liste de dict - CO_No, CO_Nom, CO_Prenom, CO_Caissier.

    Erreurs possibles : ErreurConnexion si la lecture échoue côté SQL Server.

    Exemple :
        lister_collaborateurs_sage(connexion)
    """
    return connexion.executer_lecture(
        "SELECT CO_No, CO_Nom, CO_Prenom, CO_Caissier FROM F_COLLABORATEUR ORDER BY CO_Nom, CO_Prenom"
    )


def lire_collaborateur_sage(connexion, co_no: int) -> dict | None:
    """Lit un collaborateur Sage par CO_No, ou None si il n'existe pas."""
    if co_no is None:
        raise ErreurValidation("[VALIDATION] Le numéro de collaborateur Sage (CO_No) est obligatoire.")
    lignes = connexion.executer_lecture(
        "SELECT CO_No, CO_Nom, CO_Prenom, CO_Caissier FROM F_COLLABORATEUR WHERE CO_No = ?", [co_no]
    )
    return lignes[0] if lignes else None
