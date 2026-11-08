"""
Service de synchronisation des référentiels Sage (Phase 12) : tiers
(F_COMPTET) et collaborateurs (F_COLLABORATEUR), pour remplacer les
champs libres "Bénéficiaire (code tiers Sage)" et "Responsable (code
collaborateur Sage)" du formulaire d'opération par des combobox de noms
réels.

Lecture SEULE sur BIJOU (objets_metier.lecture_sage) - aucune écriture
n'est jamais effectuée sur Sage.

Contrairement aux caisses (service_synchronisation_caisses.py),
TIERS_SAGE et COLLABORATEURS_SAGE sont des miroirs purs : aucun champ
propre à l'application n'existe sur ces deux tables, donc chaque
synchronisation réécrit intégralement Nom/Intitule (pas de distinction
création/mise à jour à préserver) - clé d'appariement = CT_Num / CO_No
(identifiants réels Sage, jamais le nom).
"""

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import ErreurSQL, ErreurValidation, message_sql_lisible, message_succes
from gestion_erreurs.journal import obtenir_journal
from modeles.collaborateur_sage import CollaborateurSage
from modeles.tiers_sage import TiersSage
from objets_metier import lecture_sage
from services import droits

journal = obtenir_journal()


def synchroniser_referentiels_depuis_sage(connexion_sage, utilisateur_id: int) -> dict:
    """
    Objectif : synchroniser TIERS_SAGE et COLLABORATEURS_SAGE avec BIJOU.

    Parametres :
        connexion_sage : une ConnexionSageLectureSeule déjà utilisable
            (ou un objet de test exposant la même méthode executer_lecture()).
        utilisateur_id (int) : doit être MANAGER.

    Retour : dict {"succes": True, "message": str, "tiers": int, "collaborateurs": int}.

    Erreurs possibles : ErreurValidation (droits, mode lecture seule), ErreurSQL.

    Exemple :
        synchroniser_referentiels_depuis_sage(ConnexionSageLectureSeule(), utilisateur_id=1)
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        droits.exiger_role(utilisateur, ("MANAGER",))

        tiers_sage = lecture_sage.lister_tiers_sage(connexion_sage)
        collaborateurs_sage = lecture_sage.lister_collaborateurs_sage(connexion_sage)
        maintenant = datetime.now(timezone.utc)

        for tiers in tiers_sage:
            ligne = session.get(TiersSage, tiers["CT_Num"])
            if ligne is None:
                session.add(TiersSage(
                    CT_Num=tiers["CT_Num"], Intitule=tiers["CT_Intitule"] or tiers["CT_Num"],
                    Type_Tiers=tiers["CT_Type"], Derniere_Synchro_Sage=maintenant,
                ))
            else:
                ligne.Intitule = tiers["CT_Intitule"] or ligne.Intitule
                ligne.Type_Tiers = tiers["CT_Type"]
                ligne.Derniere_Synchro_Sage = maintenant

        for collaborateur in collaborateurs_sage:
            nom_complet = " ".join(p for p in [collaborateur["CO_Nom"], collaborateur["CO_Prenom"]] if p).strip()
            ligne = session.get(CollaborateurSage, collaborateur["CO_No"])
            if ligne is None:
                session.add(CollaborateurSage(
                    CO_No=collaborateur["CO_No"], Nom_Complet=nom_complet or f"Collaborateur {collaborateur['CO_No']}",
                    Caissier=bool(collaborateur["CO_Caissier"]), Derniere_Synchro_Sage=maintenant,
                ))
            else:
                ligne.Nom_Complet = nom_complet or ligne.Nom_Complet
                ligne.Caissier = bool(collaborateur["CO_Caissier"])
                ligne.Derniere_Synchro_Sage = maintenant

        session.commit()

        # Relecture de contrôle - jamais de [SUCCES] sans confirmation réelle.
        nb_tiers_en_base = session.query(TiersSage).count()
        nb_collaborateurs_en_base = session.query(CollaborateurSage).count()
        if nb_tiers_en_base < len(tiers_sage) or nb_collaborateurs_en_base < len(collaborateurs_sage):
            raise ErreurSQL("[ERREUR] La synchronisation des référentiels n'a pas pu être confirmée par relecture.")

        journal.info(
            f"Synchronisation référentiels Sage : {len(tiers_sage)} tiers, {len(collaborateurs_sage)} collaborateurs "
            f"(déclenchée par utilisateur {utilisateur_id})."
        )
        return {
            "succes": True,
            "message": message_succes(
                f"Référentiels synchronisés : {len(tiers_sage)} tiers, {len(collaborateurs_sage)} collaborateur(s)."
            ),
            "tiers": len(tiers_sage),
            "collaborateurs": len(collaborateurs_sage),
        }
    except ErreurValidation:
        session.rollback()
        raise
    except SQLAlchemyError as erreur:
        session.rollback()
        journal.error(f"Synchronisation référentiels Sage échouée : {erreur}")
        raise ErreurSQL(f"[ERREUR] Synchronisation impossible : {message_sql_lisible(erreur)}") from erreur
    finally:
        session.close()


def lister_tiers() -> dict:
    """
    Objectif : lister les tiers Sage déjà synchronisés (pour la combobox
    "Bénéficiaire" du frontend).

    Exemple :
        lister_tiers()
    """
    session = obtenir_session()
    try:
        lignes = session.query(TiersSage).order_by(TiersSage.Intitule).all()
        resultats = [{"CT_Num": l.CT_Num, "Intitule": l.Intitule} for l in lignes]
        return {"succes": True, "message": message_succes(f"{len(resultats)} tiers trouvé(s)."), "resultats": resultats}
    finally:
        session.close()


def lister_collaborateurs() -> dict:
    """
    Objectif : lister les collaborateurs Sage déjà synchronisés (pour la
    combobox "Responsable" du frontend).

    Exemple :
        lister_collaborateurs()
    """
    session = obtenir_session()
    try:
        lignes = session.query(CollaborateurSage).order_by(CollaborateurSage.Nom_Complet).all()
        resultats = [{"CO_No": l.CO_No, "Nom_Complet": l.Nom_Complet, "Caissier": l.Caissier} for l in lignes]
        return {"succes": True, "message": message_succes(f"{len(resultats)} collaborateur(s) trouvé(s)."), "resultats": resultats}
    finally:
        session.close()
