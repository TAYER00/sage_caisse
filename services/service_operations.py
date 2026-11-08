"""
Service métier "Opération de caisse" - CRUD de base (Phase 4) + workflow
complet, historique et calcul des soldes (Phase 5).

Règles de droits et de transitions : voir 00_analyse/05_PHASE5_WORKFLOW.md,
00_analyse/09_PHASE9_MODIF_SUPPRESSION.md et 00_analyse/10_PHASE10_ANNULE_EQUIVALENT_BROUILLON.md.
Rappel des règles absolues (Phase 10 - BROUILLON et ANNULE équivalents) :
    - Une opération en BROUILLON ou ANNULE (STATUTS_MODIFIABLES) peut être
      MODIFIÉE (tous champs), SUPPRIMÉE (réservé MANAGER) ou VALIDÉE
      directement (réservé MANAGER).
    - Une opération VALIDE est verrouillée (lecture seule, non
      supprimable) - sa seule porte de sortie est "remettre en brouillon",
      réservée au MANAGER.
    - Une opération COMPTABILISE reste strictement figée (aucune des
      actions ci-dessus).
    - Jamais de [SUCCES] avant une relecture de contrôle confirmant la
      persistance réelle (règle reprise de sage_to_shopify).
    - Jamais de double validation/comptabilisation silencieuse - toute
      transition déjà faite est explicitement refusée.
"""

import shutil
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import (
    ErreurSQL,
    ErreurValidation,
    message_sql_lisible,
    message_succes,
)
from modeles.caisse import Caisse
from modeles.historique import HistoriqueCaisse
from modeles.justificatif import JustificatifCaisse
from modeles.operation import OperationCaisse
from modeles.utilisateur import Utilisateur
from modeles.validation import ValidationCaisse
from services import droits, service_caisses
from services.service_justificatifs import DOSSIER_STOCKAGE as DOSSIER_STOCKAGE_JUSTIFICATIFS

TYPES_VALIDES = ("ALIMENTATION", "DEPENSE", "REMBOURSEMENT")
SENS_IMPOSE = {"ALIMENTATION": "ENTREE", "DEPENSE": "SORTIE"}  # REMBOURSEMENT : choisi explicitement

# Phase 10 : BROUILLON et ANNULE se comportent de façon identique - modifiables,
# supprimables, et validables directement. Seul VALIDE est verrouillé (lecture
# seule), avec comme unique porte de sortie "remettre en brouillon" (MANAGER).
STATUTS_MODIFIABLES = ("BROUILLON", "ANNULE")


def _ecrire_historique(session, id_operation: int, champ: str, ancienne_valeur, nouvelle_valeur, utilisateur: int) -> None:
    """Trace une modification de champ - jamais modifiée après coup (journal d'ajout seul)."""
    session.add(HistoriqueCaisse(
        Id_Operation=id_operation, Champ_Modifie=champ,
        Ancienne_Valeur=None if ancienne_valeur is None else str(ancienne_valeur),
        Nouvelle_Valeur=None if nouvelle_valeur is None else str(nouvelle_valeur),
        Utilisateur=utilisateur,
    ))


def _ecrire_validation(session, id_operation: int, action: str, utilisateur: int, commentaire: str = None) -> None:
    """Trace une action de workflow (Validation/Annulation/Comptabilisation/Remise en brouillon)."""
    session.add(ValidationCaisse(Id_Operation=id_operation, Action=action, Utilisateur=utilisateur, Commentaire=commentaire))


def _generer_reference(session) -> str:
    """Numéro automatique simple : OP-<année>-<compteur sur 6 chiffres>."""
    annee = datetime.now(timezone.utc).year
    prefixe = f"OP-{annee}-"
    nb_existantes = session.query(OperationCaisse).filter(OperationCaisse.Reference.like(f"{prefixe}%")).count()
    return f"{prefixe}{nb_existantes + 1:06d}"


def creer_operation(
    type_operation: str,
    id_caisse: int,
    date_operation: datetime,
    montant: float,
    cree_par: int,
    sens_solde: str = None,
    id_motif: int = None,
    beneficiaire: str = None,
    responsable: int = None,
    societe: str = None,
    compte_financier: str = None,
    compte_analytique: str = None,
    devise: str = "EUR",
    projet: str = None,
    observation: str = None,
) -> dict:
    """
    Objectif : créer une nouvelle opération de caisse, toujours en statut
    BROUILLON (la validation est une action séparée, Phase 5).

    Parametres principaux :
        type_operation (str) : "ALIMENTATION", "DEPENSE" ou "REMBOURSEMENT".
        id_caisse (int) : caisse concernée, doit exister.
        date_operation (datetime) : date de l'opération.
        montant (float) : doit être strictement positif.
        cree_par (int) : identifiant de l'utilisateur créateur, doit exister.
        sens_solde (str, optionnel) : "ENTREE"/"SORTIE" - OBLIGATOIRE pour
            un REMBOURSEMENT (jamais déduit automatiquement, règle du
            prompt), imposé automatiquement pour les deux autres types.

    Retour : dict {"succes": True, "message": str, "id": int, "reference": str}.

    Validations :
        - type_operation valide, caisse existante, montant > 0,
        - sens_solde cohérent avec le type (imposé pour
          Alimentation/Dépense, exigé explicitement pour Remboursement),
        - créateur (cree_par) existant.

    Erreurs possibles : ErreurValidation, ErreurSQL.

    Exemple :
        creer_operation("DEPENSE", id_caisse=1, date_operation=datetime.now(),
                         montant=45.90, cree_par=1, projet="Déplacement Lyon",
                         observation="Taxi aéroport")
    """
    droits.verifier_ecriture_autorisee()
    if type_operation not in TYPES_VALIDES:
        raise ErreurValidation(f"[VALIDATION] Type d'opération invalide : {type_operation}. Attendu : {TYPES_VALIDES}.")
    if id_caisse is None:
        raise ErreurValidation("[VALIDATION] Veuillez sélectionner une caisse.")
    if montant is None or montant <= 0:
        raise ErreurValidation("[VALIDATION] Le montant doit être supérieur à zéro.")
    if date_operation is None:
        raise ErreurValidation("[VALIDATION] La date de l'opération est obligatoire.")
    if cree_par is None:
        raise ErreurValidation("[VALIDATION] L'utilisateur créateur est obligatoire.")

    if type_operation in SENS_IMPOSE:
        sens_solde_final = SENS_IMPOSE[type_operation]
    else:  # REMBOURSEMENT
        if sens_solde not in ("ENTREE", "SORTIE"):
            raise ErreurValidation(
                "[VALIDATION] Pour un remboursement, vous devez indiquer explicitement "
                "si cela augmente (ENTREE) ou diminue (SORTIE) le solde de la caisse "
                "- ce sens n'est jamais déduit automatiquement."
            )
        sens_solde_final = sens_solde

    session = obtenir_session()
    try:
        if session.get(Caisse, id_caisse) is None:
            raise ErreurValidation(f"[VALIDATION] La caisse {id_caisse} n'existe pas.")
        if session.get(Utilisateur, cree_par) is None:
            raise ErreurValidation(f"[VALIDATION] L'utilisateur créateur {cree_par} n'existe pas.")

        operation = OperationCaisse(
            Reference=_generer_reference(session),
            Type_Operation=type_operation,
            Sens_Solde=sens_solde_final,
            Id_Caisse=id_caisse,
            Date_Operation=date_operation,
            Id_Motif=id_motif,
            Beneficiaire=beneficiaire,
            Responsable=responsable,
            Societe=societe,
            Compte_Financier=compte_financier,
            Compte_Analytique=compte_analytique,
            Montant=montant,
            Devise=devise,
            Projet=projet,
            Observation=observation,
            Statut="BROUILLON",
            Cree_Par=cree_par,
        )
        session.add(operation)
        session.commit()

        # Relecture de contrôle - jamais de [SUCCES] sans confirmation réelle.
        confirmation = session.get(OperationCaisse, operation.Id_Operation)
        if confirmation is None:
            raise ErreurSQL("[ERREUR] La création de l'opération n'a pas pu être confirmée par relecture.")

        return {
            "succes": True,
            "message": message_succes(f"Opération '{confirmation.Reference}' enregistrée avec succès."),
            "id": confirmation.Id_Operation,
            "reference": confirmation.Reference,
        }
    except ErreurValidation:
        session.rollback()
        raise
    except IntegrityError as erreur:
        session.rollback()
        raise ErreurValidation(f"[VALIDATION] Données invalides : {message_sql_lisible(erreur)}") from erreur
    except SQLAlchemyError as erreur:
        session.rollback()
        raise ErreurSQL(f"[ERREUR] Création de l'opération impossible : {message_sql_lisible(erreur)}") from erreur
    finally:
        session.close()


def lire_operation(id_operation: int) -> dict:
    """
    Objectif : lire une opération par son identifiant.

    Erreurs possibles : ErreurValidation si l'opération n'existe pas.

    Exemple :
        lire_operation(1)
    """
    session = obtenir_session()
    try:
        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        return {
            "succes": True,
            "message": message_succes(f"Opération '{operation.Reference}' lue avec succès."),
            "donnees": _vers_dict(operation),
        }
    finally:
        session.close()


def lister_operations(
    id_caisse: int = None,
    projet: str = None,
    responsable: int = None,
    statut: str = None,
    recherche_texte: str = None,
) -> dict:
    """
    Objectif : lister les opérations, avec filtres optionnels - reprend
    exactement les besoins identifiés en Phase 2
    (00_analyse/02_DICTIONNAIRE_FONCTIONNEL_CAISSE.md, section 5.2) :
    par caisse, par projet, par responsable, recherche libre.

    Exemple :
        lister_operations(id_caisse=1, projet="Déplacement Lyon")
        lister_operations(recherche_texte="taxi")
    """
    session = obtenir_session()
    try:
        requete = session.query(OperationCaisse)
        if id_caisse is not None:
            requete = requete.filter(OperationCaisse.Id_Caisse == id_caisse)
        if projet:
            requete = requete.filter(OperationCaisse.Projet == projet)
        if responsable is not None:
            requete = requete.filter(OperationCaisse.Responsable == responsable)
        if statut:
            requete = requete.filter(OperationCaisse.Statut == statut)
        if recherche_texte:
            motif = f"%{recherche_texte}%"
            requete = requete.filter(
                or_(
                    OperationCaisse.Observation.like(motif),
                    OperationCaisse.Projet.like(motif),
                    OperationCaisse.Reference.like(motif),
                )
            )
        operations = requete.order_by(OperationCaisse.Date_Operation.desc()).all()
        resultats = [_vers_dict(o) for o in operations]
        return {
            "succes": True,
            "message": message_succes(f"{len(resultats)} opération(s) trouvée(s)."),
            "resultats": resultats,
        }
    finally:
        session.close()


def modifier_operation(id_operation: int, utilisateur_id: int, **champs) -> dict:
    """
    Objectif : modifier N'IMPORTE QUEL champ métier d'une opération -
    UNIQUEMENT si elle est en BROUILLON ou ANNULE (règle Phase 10 : ces
    deux statuts se comportent de façon identique - modifiables,
    supprimables, validables directement ; VALIDE/COMPTABILISE restent en
    lecture seule), et uniquement par son créateur ou un MANAGER.

    Parametres :
        id_operation (int) : opération à modifier.
        utilisateur_id (int) : utilisateur qui demande la modification -
            tracé dans l'historique.
        **champs : champs à modifier (ex: Montant=50, Projet="Autre projet",
            Type_Operation="REMBOURSEMENT", Sens_Solde="ENTREE",
            Id_Caisse=2...). Seuls les champs explicitement fournis sont
            modifiés (même principe que sage_to_shopify : jamais de valeur
            par défaut écrasant un champ non transmis). Chaque champ
            réellement modifié est tracé dans HISTORIQUE_CAISSE.

            Cas particulier Type_Operation/Sens_Solde : mêmes règles qu'à
            la création (voir creer_operation) - le sens est imposé pour
            ALIMENTATION/DEPENSE (toute valeur fournie est ignorée), et
            doit être fourni explicitement si le type devient
            REMBOURSEMENT (jamais déduit automatiquement).

    Erreurs possibles : ErreurValidation (opération introuvable, pas en
    brouillon, montant/caisse/type invalide, droits insuffisants).

    Exemple :
        modifier_operation(1, utilisateur_id=2, Montant=52.30, Observation="Taxi + pourboire")
    """
    droits.verifier_ecriture_autorisee()
    if not champs:
        raise ErreurValidation("[VALIDATION] Aucune donnée à modifier n'a été fournie.")
    if "Montant" in champs and (champs["Montant"] is None or champs["Montant"] <= 0):
        raise ErreurValidation("[VALIDATION] Le montant doit être supérieur à zéro.")
    if "Id_Caisse" in champs and champs["Id_Caisse"] is None:
        raise ErreurValidation("[VALIDATION] Veuillez sélectionner une caisse.")
    if "Date_Operation" in champs and champs["Date_Operation"] is None:
        raise ErreurValidation("[VALIDATION] La date de l'opération est obligatoire.")

    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut not in STATUTS_MODIFIABLES:
            raise ErreurValidation(
                f"[VALIDATION] Cette opération est '{operation.Statut}' - seule une opération "
                f"en BROUILLON ou ANNULE peut être modifiée."
            )
        droits.exiger_createur_ou_manager(utilisateur, operation.Cree_Par)

        if "Id_Caisse" in champs and session.get(Caisse, champs["Id_Caisse"]) is None:
            raise ErreurValidation(f"[VALIDATION] La caisse {champs['Id_Caisse']} n'existe pas.")

        if "Type_Operation" in champs or "Sens_Solde" in champs:
            type_final = champs.get("Type_Operation", operation.Type_Operation)
            if type_final not in TYPES_VALIDES:
                raise ErreurValidation(f"[VALIDATION] Type d'opération invalide : {type_final}. Attendu : {TYPES_VALIDES}.")
            if type_final in SENS_IMPOSE:
                champs["Sens_Solde"] = SENS_IMPOSE[type_final]
            else:  # REMBOURSEMENT
                devient_remboursement = champs.get("Type_Operation") == "REMBOURSEMENT" and operation.Type_Operation != "REMBOURSEMENT"
                sens_fourni = champs.get("Sens_Solde")
                if devient_remboursement and sens_fourni not in ("ENTREE", "SORTIE"):
                    raise ErreurValidation(
                        "[VALIDATION] Pour un remboursement, vous devez indiquer explicitement "
                        "si cela augmente (ENTREE) ou diminue (SORTIE) le solde de la caisse "
                        "- ce sens n'est jamais déduit automatiquement."
                    )
                champs["Sens_Solde"] = sens_fourni if sens_fourni in ("ENTREE", "SORTIE") else operation.Sens_Solde
            champs["Type_Operation"] = type_final

        anciennes_valeurs = {champ: getattr(operation, champ) for champ in champs}
        for champ, valeur in champs.items():
            setattr(operation, champ, valeur)
        operation.Date_Modification = datetime.now(timezone.utc)
        operation.Modifie_Par = utilisateur_id
        for champ, nouvelle_valeur in champs.items():
            _ecrire_historique(session, id_operation, champ, anciennes_valeurs[champ], nouvelle_valeur, utilisateur_id)
        session.commit()

        confirmation = session.get(OperationCaisse, id_operation)
        for champ, valeur in champs.items():
            valeur_relue = getattr(confirmation, champ)
            # Montant est un NUMERIC -> relu comme Decimal : comparer en float
            # pour éviter un faux écart entre Decimal("52.30") et float 52.3.
            if isinstance(valeur_relue, Decimal):
                valeur_relue, valeur = float(valeur_relue), float(valeur)
            if valeur_relue != valeur:
                raise ErreurSQL(f"[ERREUR] La modification de '{champ}' n'a pas pu être confirmée par relecture.")

        return {"succes": True, "message": message_succes(f"Opération '{confirmation.Reference}' modifiée avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def supprimer_operation(id_operation: int, utilisateur_id: int, confirmer: bool = False) -> dict:
    """
    Objectif : supprimer directement une opération en BROUILLON ou ANNULE
    - réservé EXCLUSIVEMENT aux MANAGER (règle explicite : contrairement à
    la modification ou à l'annulation, le créateur seul ne peut pas
    supprimer, même sa propre opération).

    Parametres : confirmer (bool) doit valoir True.

    Erreurs possibles : ErreurValidation (non confirmé, introuvable, pas
    en brouillon/annulée, droits insuffisants - rôle autre que MANAGER).

    Note technique : les tables HISTORIQUE_CAISSE/VALIDATIONS_CAISSE/
    JUSTIFICATIFS_CAISSE référencent l'opération par clé étrangère SANS
    suppression en cascade au niveau SQL Server - leurs lignes (et les
    fichiers justificatifs sur disque) sont donc purgées explicitement ici
    avant de supprimer l'opération, sinon SQL Server refuse le DELETE
    (violation de contrainte). Trouvé en testant réellement contre la
    vraie base (invisible avec SQLite en mémoire, qui n'impose pas les
    clés étrangères par défaut).

    Exemple :
        supprimer_operation(1, utilisateur_id=1, confirmer=True)
    """
    droits.verifier_ecriture_autorisee()
    if not confirmer:
        raise ErreurValidation("[VALIDATION] Suppression non confirmée : passez confirmer=True.")

    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut not in STATUTS_MODIFIABLES:
            raise ErreurValidation(
                f"[VALIDATION] Cette opération est '{operation.Statut}' - seule une opération "
                f"en BROUILLON ou ANNULE peut être supprimée."
            )
        droits.exiger_role(utilisateur, ("MANAGER",))

        reference = operation.Reference
        session.query(HistoriqueCaisse).filter(HistoriqueCaisse.Id_Operation == id_operation).delete()
        session.query(ValidationCaisse).filter(ValidationCaisse.Id_Operation == id_operation).delete()
        session.query(JustificatifCaisse).filter(JustificatifCaisse.Id_Operation == id_operation).delete()
        session.delete(operation)
        session.commit()

        dossier_justificatifs = DOSSIER_STOCKAGE_JUSTIFICATIFS / str(id_operation)
        shutil.rmtree(dossier_justificatifs, ignore_errors=True)

        return {"succes": True, "message": message_succes(f"Opération '{reference}' supprimée avec succès.")}
    finally:
        session.close()


# --- Workflow (Phase 5) ------------------------------------------------------

def valider_operation(id_operation: int, utilisateur_id: int, commentaire: str = None) -> dict:
    """
    Objectif : valider une opération en BROUILLON OU ANNULE (passage
    direct à VALIDE - règle Phase 10, pas besoin de repasser par
    "remettre en brouillon" pour revalider une opération annulée).
    Réservé aux MANAGER (voir 00_analyse/05_PHASE5_WORKFLOW.md).

    Erreurs possibles : ErreurValidation (introuvable, déjà validée/autre
    statut, droits insuffisants).

    Exemple :
        valider_operation(1, utilisateur_id=1, commentaire="Pièce conforme.")
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        droits.exiger_role(utilisateur, ("MANAGER",))

        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut == "VALIDE":
            raise ErreurValidation("[VALIDATION] Cette opération a déjà été validée.")
        if operation.Statut not in STATUTS_MODIFIABLES:
            raise ErreurValidation(f"[VALIDATION] Une opération '{operation.Statut}' ne peut pas être validée.")

        operation.Statut = "VALIDE"
        operation.Valide_Par = utilisateur_id
        operation.Date_Validation = datetime.now(timezone.utc)
        _ecrire_validation(session, id_operation, "VALIDATION", utilisateur_id, commentaire)
        session.flush()
        service_caisses.recalculer_solde(operation.Id_Caisse, session=session)
        session.commit()

        confirmation = session.get(OperationCaisse, id_operation)
        if confirmation.Statut != "VALIDE":
            raise ErreurSQL("[ERREUR] La validation n'a pas pu être confirmée par relecture.")

        return {"succes": True, "message": message_succes(f"Opération '{confirmation.Reference}' validée avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def annuler_operation(id_operation: int, utilisateur_id: int, commentaire: str = None) -> dict:
    """
    Objectif : annuler une opération (BROUILLON ou VALIDE -> ANNULE).
    Droits : le créateur peut annuler son propre BROUILLON ; seul un
    MANAGER peut annuler une opération déjà VALIDE.

    Erreurs possibles : ErreurValidation (introuvable, déjà
    annulée/comptabilisée, droits insuffisants).

    Exemple :
        annuler_operation(1, utilisateur_id=2)
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut == "ANNULE":
            raise ErreurValidation("[VALIDATION] Cette opération a déjà été annulée.")
        if operation.Statut == "COMPTABILISE":
            raise ErreurValidation(
                "[VALIDATION] Une opération comptabilisée ne peut pas être annulée directement - "
                "une régularisation séparée est nécessaire."
            )

        if operation.Statut == "BROUILLON":
            droits.exiger_createur_ou_manager(utilisateur, operation.Cree_Par)
        else:  # VALIDE
            droits.exiger_role(utilisateur, ("MANAGER",))

        statut_precedent = operation.Statut
        operation.Statut = "ANNULE"
        _ecrire_validation(session, id_operation, "ANNULATION", utilisateur_id, commentaire)
        session.flush()
        if statut_precedent == "VALIDE":
            # L'opération sort du calcul du solde - recalcul nécessaire.
            service_caisses.recalculer_solde(operation.Id_Caisse, session=session)
        session.commit()

        confirmation = session.get(OperationCaisse, id_operation)
        if confirmation.Statut != "ANNULE":
            raise ErreurSQL("[ERREUR] L'annulation n'a pas pu être confirmée par relecture.")

        return {"succes": True, "message": message_succes(f"Opération '{confirmation.Reference}' annulée avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def comptabiliser_operation(id_operation: int, utilisateur_id: int, reference_comptable_sage: int = None, commentaire: str = None) -> dict:
    """
    Objectif : comptabiliser une opération VALIDE (passage à
    COMPTABILISE). Réservé aux MANAGER.

    IMPORTANT (rappel du prompt) : ceci n'écrit RIEN dans Sage. C'est un
    statut interne - la comptabilisation réelle dans Sage sera étudiée
    séparément. `reference_comptable_sage` reste optionnel, à renseigner
    manuellement si une référence Sage existe déjà par ailleurs.

    Erreurs possibles : ErreurValidation (introuvable, pas VALIDE, droits
    insuffisants).

    Exemple :
        comptabiliser_operation(2, utilisateur_id=1, reference_comptable_sage=94812)
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        droits.exiger_role(utilisateur, ("MANAGER",))

        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut == "COMPTABILISE":
            raise ErreurValidation("[VALIDATION] Cette opération a déjà été comptabilisée.")
        if operation.Statut != "VALIDE":
            raise ErreurValidation(
                f"[VALIDATION] Seule une opération VALIDE peut être comptabilisée (statut actuel : '{operation.Statut}')."
            )

        operation.Statut = "COMPTABILISE"
        operation.Comptabilise_Par = utilisateur_id
        operation.Date_Comptabilisation = datetime.now(timezone.utc)
        if reference_comptable_sage is not None:
            operation.Reference_Comptable_Sage = reference_comptable_sage
        _ecrire_validation(session, id_operation, "COMPTABILISATION", utilisateur_id, commentaire)
        session.flush()
        service_caisses.recalculer_solde(operation.Id_Caisse, session=session)  # reste VALIDE+COMPTABILISE, change rarement le total mais recalculé par cohérence
        session.commit()

        confirmation = session.get(OperationCaisse, id_operation)
        if confirmation.Statut != "COMPTABILISE":
            raise ErreurSQL("[ERREUR] La comptabilisation n'a pas pu être confirmée par relecture.")

        return {"succes": True, "message": message_succes(f"Opération '{confirmation.Reference}' comptabilisée avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def remettre_en_brouillon(id_operation: int, utilisateur_id: int, commentaire: str = None) -> dict:
    """
    Objectif : repasser une opération VALIDE ou ANNULE en BROUILLON (pour
    l'ANNULE : afin de pouvoir la corriger puis la revalider, plutôt que
    de la recréer). Réservé aux MANAGER (règle explicite du prompt :
    "uniquement si autorisé").

    Erreurs possibles : ErreurValidation (introuvable, pas VALIDE/ANNULE,
    droits insuffisants).

    Exemple :
        remettre_en_brouillon(1, utilisateur_id=1, commentaire="Erreur de montant à corriger.")
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        droits.exiger_role(utilisateur, ("MANAGER",))

        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut not in ("VALIDE", "ANNULE"):
            raise ErreurValidation(
                f"[VALIDATION] Seule une opération VALIDE ou ANNULE peut être remise en brouillon (statut actuel : '{operation.Statut}')."
            )

        statut_precedent = operation.Statut
        operation.Statut = "BROUILLON"
        operation.Valide_Par = None
        operation.Date_Validation = None
        _ecrire_validation(session, id_operation, "REMISE_BROUILLON", utilisateur_id, commentaire)
        session.flush()
        if statut_precedent == "VALIDE":
            # L'opération sortait du calcul du solde - recalcul nécessaire (une
            # ANNULE n'y était déjà plus comptée, inutile de recalculer pour rien).
            service_caisses.recalculer_solde(operation.Id_Caisse, session=session)
        session.commit()

        confirmation = session.get(OperationCaisse, id_operation)
        if confirmation.Statut != "BROUILLON":
            raise ErreurSQL("[ERREUR] La remise en brouillon n'a pas pu être confirmée par relecture.")

        return {"succes": True, "message": message_succes(f"Opération '{confirmation.Reference}' remise en brouillon avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def _vers_dict(operation: OperationCaisse) -> dict:
    return {
        "Id_Operation": operation.Id_Operation,
        "Reference": operation.Reference,
        "Type_Operation": operation.Type_Operation,
        "Sens_Solde": operation.Sens_Solde,
        "Id_Caisse": operation.Id_Caisse,
        "Date_Operation": operation.Date_Operation.isoformat() if operation.Date_Operation else None,
        "Id_Motif": operation.Id_Motif,
        "Beneficiaire": operation.Beneficiaire,
        "Responsable": operation.Responsable,
        "Societe": operation.Societe,
        "Compte_Financier": operation.Compte_Financier,
        "Compte_Analytique": operation.Compte_Analytique,
        "Montant": float(operation.Montant),
        "Devise": operation.Devise,
        "Projet": operation.Projet,
        "Observation": operation.Observation,
        "Statut": operation.Statut,
        "Cree_Par": operation.Cree_Par,
        "Date_Creation": operation.Date_Creation.isoformat() if operation.Date_Creation else None,
        "Valide_Par": operation.Valide_Par,
        "Date_Validation": operation.Date_Validation.isoformat() if operation.Date_Validation else None,
        "Comptabilise_Par": operation.Comptabilise_Par,
        "Date_Comptabilisation": operation.Date_Comptabilisation.isoformat() if operation.Date_Comptabilisation else None,
        "Reference_Comptable_Sage": operation.Reference_Comptable_Sage,
    }


def lister_historique(id_operation: int) -> dict:
    """
    Objectif : lister les modifications tracées d'une opération (champ
    par champ, voir HISTORIQUE_CAISSE).

    Exemple :
        lister_historique(1)
    """
    session = obtenir_session()
    try:
        lignes = (
            session.query(HistoriqueCaisse)
            .filter(HistoriqueCaisse.Id_Operation == id_operation)
            .order_by(HistoriqueCaisse.Date_Modification.desc())
            .all()
        )
        resultats = [
            {
                "Champ_Modifie": l.Champ_Modifie, "Ancienne_Valeur": l.Ancienne_Valeur,
                "Nouvelle_Valeur": l.Nouvelle_Valeur, "Utilisateur": l.Utilisateur,
                "Date_Modification": l.Date_Modification.isoformat() if l.Date_Modification else None,
            }
            for l in lignes
        ]
        return {"succes": True, "message": message_succes(f"{len(resultats)} modification(s) trouvée(s)."), "resultats": resultats}
    finally:
        session.close()


def lister_validations(id_operation: int) -> dict:
    """
    Objectif : lister les actions de workflow tracées d'une opération
    (Validation/Annulation/Comptabilisation/Remise en brouillon).

    Exemple :
        lister_validations(1)
    """
    session = obtenir_session()
    try:
        lignes = (
            session.query(ValidationCaisse)
            .filter(ValidationCaisse.Id_Operation == id_operation)
            .order_by(ValidationCaisse.Date_Action.desc())
            .all()
        )
        resultats = [
            {
                "Action": l.Action, "Utilisateur": l.Utilisateur,
                "Date_Action": l.Date_Action.isoformat() if l.Date_Action else None,
                "Commentaire": l.Commentaire,
            }
            for l in lignes
        ]
        return {"succes": True, "message": message_succes(f"{len(resultats)} action(s) trouvée(s)."), "resultats": resultats}
    finally:
        session.close()
