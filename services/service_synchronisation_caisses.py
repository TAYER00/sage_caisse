"""
Service de synchronisation des caisses depuis BIJOU (Phase 11, prompt_4.txt).

Lecture SEULE sur BIJOU (objets_metier.lecture_sage.lister_caisses_sage) -
aucune écriture n'est jamais effectuée sur Sage, pour les raisons
détaillées dans 00_analyse/11_PHASE1_ANALYSE_SYNC_BIJOU.md (les caisses
réelles existent déjà et sont complètes côté Sage ; les colonnes "cb*" de
F_CAISSE rendent de toute façon toute écriture directe risquée).

Stratégie "upsert" idempotente, clé d'appariement = Numero_Caisse_Sage
(jamais le nom - règle explicite du prompt, pour éviter les doublons) :
    - Numero_Caisse_Sage déjà connu en base -> met à jour UNIQUEMENT
      Societe (donnée de référence Sage pure) et Derniere_Synchro_Sage.
      Nom_Caisse N'EST JAMAIS RÉÉCRIT sur une caisse existante - une fois
      créée, son nom devient une donnée propre à l'application (ex. "Caisse
      Principale Siège", choisi par l'utilisateur), pas un simple reflet
      de CA_Intitule - l'écraser à chaque synchro violerait la règle du
      prompt "ne pas écraser les données locales existantes" (constaté une
      fois en conditions réelles lors de la mise au point de cette
      fonction, corrigé avant la fin de la Phase 11).
      Solde_Initial/Solde_Actuel/Statut et toutes les OPERATIONS_CAISSE
      déjà liées restent eux aussi strictement intacts.
    - Numero_Caisse_Sage inconnu -> création d'une nouvelle caisse (son
      Nom_Caisse initial reprend CA_Intitule, faute de mieux - aucune
      modification de caisse n'existe encore dans ce projet pour le
      renommer ensuite, mais une resynchronisation ultérieure ne
      l'écrasera en tout cas jamais, par construction). Solde_Initial/
      Solde_Actuel = 0, Statut = ACTIF par défaut, comme creer_caisse().
    - Une caisse applicative sans Numero_Caisse_Sage (créée sans lien
      Sage) n'est jamais touchée ni supprimée par cette synchronisation.
"""

from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import ErreurSQL, ErreurValidation, message_sql_lisible, message_succes
from gestion_erreurs.journal import obtenir_journal
from modeles.caisse import Caisse
from objets_metier import lecture_sage
from services import droits

journal = obtenir_journal()


def synchroniser_caisses_depuis_sage(connexion_sage, utilisateur_id: int) -> dict:
    """
    Objectif : synchroniser les caisses applicatives avec les caisses
    réelles de BIJOU (lecture seule sur Sage, écriture uniquement dans
    SAGE_CAISSE_APP) - répétable sans créer de doublons.

    Parametres :
        connexion_sage : une ConnexionSageLectureSeule déjà utilisable
            (ou un objet de test exposant la même méthode
            executer_lecture()).
        utilisateur_id (int) : utilisateur qui déclenche la
            synchronisation - doit être MANAGER (action sensible).

    Retour : dict {"succes": True, "message": str, "creees": int,
                   "mises_a_jour": int, "total_sage": int}.

    Erreurs possibles : ErreurValidation (droits insuffisants, mode
    lecture seule actif), ErreurSQL, ErreurConnexion (lecture Sage
    impossible).

    Exemple :
        synchroniser_caisses_depuis_sage(ConnexionSageLectureSeule(), utilisateur_id=1)
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        droits.exiger_role(utilisateur, ("MANAGER",))

        caisses_sage = lecture_sage.lister_caisses_sage(connexion_sage)
        maintenant = datetime.now(timezone.utc)
        nb_creees = 0
        nb_mises_a_jour = 0

        for caisse_sage in caisses_sage:
            ca_no = caisse_sage["CA_No"]
            caisse_app = session.query(Caisse).filter(Caisse.Numero_Caisse_Sage == ca_no).first()
            if caisse_app is None:
                session.add(Caisse(
                    Code_Caisse=f"SAGE-{ca_no}",
                    Nom_Caisse=caisse_sage["CA_Intitule"] or f"Caisse Sage {ca_no}",
                    Societe=caisse_sage["Societe"],
                    Numero_Caisse_Sage=ca_no,
                    Derniere_Synchro_Sage=maintenant,
                ))
                nb_creees += 1
            else:
                # Nom_Caisse volontairement PAS touché ici - voir docstring du module.
                caisse_app.Societe = caisse_sage["Societe"]
                caisse_app.Derniere_Synchro_Sage = maintenant
                nb_mises_a_jour += 1
        session.commit()

        # Relecture de contrôle - jamais de [SUCCES] sans confirmation réelle.
        numeros_sage = [c["CA_No"] for c in caisses_sage]
        nb_liees_en_base = (
            session.query(Caisse).filter(Caisse.Numero_Caisse_Sage.in_(numeros_sage)).count()
            if numeros_sage else 0
        )
        if nb_liees_en_base != len(caisses_sage):
            raise ErreurSQL("[ERREUR] La synchronisation n'a pas pu être confirmée par relecture.")

        journal.info(
            f"Synchronisation caisses Sage : {nb_creees} créée(s), {nb_mises_a_jour} mise(s) à jour, "
            f"{len(caisses_sage)} caisse(s) Sage au total (déclenchée par utilisateur {utilisateur_id})."
        )
        return {
            "succes": True,
            "message": message_succes(
                f"Synchronisation terminée : {nb_creees} caisse(s) créée(s), {nb_mises_a_jour} mise(s) à jour."
            ),
            "creees": nb_creees,
            "mises_a_jour": nb_mises_a_jour,
            "total_sage": len(caisses_sage),
        }
    except ErreurValidation:
        session.rollback()
        raise
    except SQLAlchemyError as erreur:
        session.rollback()
        journal.error(f"Synchronisation caisses Sage échouée : {erreur}")
        raise ErreurSQL(f"[ERREUR] Synchronisation impossible : {message_sql_lisible(erreur)}") from erreur
    finally:
        session.close()
