"""
Service métier "Justificatif" (Phase 7 - complète la section "JUSTIFICATIFS
ET DOCUMENTS" du prompt, reportée en Phase 6).

Stockage sur disque (dossier `stockage_justificatifs/`, un sous-dossier par
opération), métadonnées en base (`JUSTIFICATIFS_CAISSE`). Contrôles de
sécurité explicitement demandés par le prompt : extensions autorisées,
taille maximale.

Règles :
    - Ajout possible tant que l'opération n'est pas ANNULE/COMPTABILISE
      (un justificatif peut être ajouté avant ou après validation).
    - Suppression (logique, jamais physique) uniquement AVANT validation
      (BROUILLON), par le créateur ou un MANAGER - règle explicite du
      prompt : "Supprimer avant validation selon les droits", "Conserver
      les justificatifs après validation".
"""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from gestion_erreurs.exceptions import ErreurSQL, ErreurValidation, message_succes
from connexion.connexion_app import obtenir_session
from modeles.justificatif import JustificatifCaisse
from modeles.operation import OperationCaisse
from services import droits

DOSSIER_STOCKAGE = Path(__file__).resolve().parent.parent / "stockage_justificatifs"
EXTENSIONS_AUTORISEES = {".pdf": "PDF", ".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG"}
TAILLE_MAX_OCTETS = 5 * 1024 * 1024  # 5 Mo


def _nom_fichier_securise(nom_original: str) -> str:
    """Retire tout ce qui n'est pas alphanumérique/point/tiret - évite toute tentative de traversée de chemin."""
    base = re.sub(r"[^A-Za-z0-9._-]", "_", nom_original)
    return base[-150:]  # évite un nom de fichier interminable


def ajouter_justificatif(id_operation: int, nom_fichier: str, contenu: bytes, utilisateur_id: int) -> dict:
    """
    Objectif : attacher un justificatif (PDF/JPG/PNG) à une opération.

    Parametres :
        id_operation (int) : opération concernée.
        nom_fichier (str) : nom original du fichier (avec extension).
        contenu (bytes) : contenu binaire du fichier.
        utilisateur_id (int) : utilisateur qui ajoute le fichier.

    Retour : dict {"succes": True, "message": str, "id": int}.

    Validations :
        - extension autorisée (.pdf/.jpg/.jpeg/.png),
        - taille <= 5 Mo,
        - opération existante, pas ANNULE/COMPTABILISE.

    Erreurs possibles : ErreurValidation, ErreurSQL.

    Exemple :
        ajouter_justificatif(1, "facture.pdf", contenu_bytes, utilisateur_id=2)
    """
    droits.verifier_ecriture_autorisee()
    if not nom_fichier:
        raise ErreurValidation("[VALIDATION] Le nom du fichier est obligatoire.")
    extension = Path(nom_fichier).suffix.lower()
    if extension not in EXTENSIONS_AUTORISEES:
        raise ErreurValidation(
            f"[VALIDATION] Extension '{extension}' non autorisée. "
            f"Formats acceptés : PDF, JPG, PNG."
        )
    if len(contenu) == 0:
        raise ErreurValidation("[VALIDATION] Le fichier est vide.")
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise ErreurValidation(f"[VALIDATION] Le fichier dépasse la taille maximale autorisée (5 Mo).")

    session = obtenir_session()
    try:
        droits.obtenir_utilisateur(session, utilisateur_id)
        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut in ("ANNULE", "COMPTABILISE"):
            raise ErreurValidation(
                f"[VALIDATION] Impossible d'ajouter un justificatif à une opération '{operation.Statut}'."
            )

        dossier_operation = DOSSIER_STOCKAGE / str(id_operation)
        dossier_operation.mkdir(parents=True, exist_ok=True)
        nom_disque = f"{uuid.uuid4().hex}_{_nom_fichier_securise(nom_fichier)}"
        chemin_disque = dossier_operation / nom_disque
        chemin_disque.write_bytes(contenu)

        justificatif = JustificatifCaisse(
            Id_Operation=id_operation, Nom_Fichier=nom_fichier,
            Chemin_Fichier=str(chemin_disque), Type_Fichier=EXTENSIONS_AUTORISEES[extension],
            Taille_Octets=len(contenu), Ajoute_Par=utilisateur_id,
        )
        session.add(justificatif)
        session.commit()

        confirmation = session.get(JustificatifCaisse, justificatif.Id_Justificatif)
        if confirmation is None:
            raise ErreurSQL("[ERREUR] L'ajout du justificatif n'a pas pu être confirmé par relecture.")

        return {
            "succes": True,
            "message": message_succes(f"Justificatif '{nom_fichier}' ajouté avec succès."),
            "id": confirmation.Id_Justificatif,
        }
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()


def lister_justificatifs(id_operation: int) -> dict:
    """
    Objectif : lister les justificatifs actifs (non supprimés) d'une opération.

    Exemple :
        lister_justificatifs(1)
    """
    session = obtenir_session()
    try:
        lignes = (
            session.query(JustificatifCaisse)
            .filter(JustificatifCaisse.Id_Operation == id_operation, JustificatifCaisse.Supprime == False)  # noqa: E712 - .is_(False) genere "IS 0", invalide sur SQL Server
            .order_by(JustificatifCaisse.Date_Ajout.desc())
            .all()
        )
        resultats = [
            {
                "Id_Justificatif": j.Id_Justificatif, "Nom_Fichier": j.Nom_Fichier,
                "Type_Fichier": j.Type_Fichier, "Taille_Octets": j.Taille_Octets,
                "Date_Ajout": j.Date_Ajout.isoformat() if j.Date_Ajout else None, "Ajoute_Par": j.Ajoute_Par,
            }
            for j in lignes
        ]
        return {"succes": True, "message": message_succes(f"{len(resultats)} justificatif(s) trouvé(s)."), "resultats": resultats}
    finally:
        session.close()


def lire_fichier_justificatif(id_justificatif: int):
    """
    Objectif : retrouver le chemin disque réel d'un justificatif, pour le
    télécharger.

    Retour : (chemin_absolu: Path, nom_fichier: str) si trouvé.

    Erreurs possibles : ErreurValidation si introuvable ou déjà supprimé.

    Exemple :
        lire_fichier_justificatif(1)
    """
    session = obtenir_session()
    try:
        justificatif = session.get(JustificatifCaisse, id_justificatif)
        if justificatif is None or justificatif.Supprime:
            raise ErreurValidation(f"[VALIDATION] Le justificatif {id_justificatif} n'existe pas.")
        chemin = Path(justificatif.Chemin_Fichier)
        if not chemin.exists():
            raise ErreurValidation(f"[VALIDATION] Le fichier de ce justificatif est introuvable sur le disque.")
        return chemin, justificatif.Nom_Fichier
    finally:
        session.close()


def supprimer_justificatif(id_justificatif: int, utilisateur_id: int) -> dict:
    """
    Objectif : supprimer (logiquement) un justificatif - UNIQUEMENT si
    l'opération associée est encore en BROUILLON, par le créateur ou un
    MANAGER (règle du prompt).

    Erreurs possibles : ErreurValidation (introuvable, opération pas en
    brouillon, droits insuffisants).

    Exemple :
        supprimer_justificatif(1, utilisateur_id=2)
    """
    droits.verifier_ecriture_autorisee()
    session = obtenir_session()
    try:
        utilisateur = droits.obtenir_utilisateur(session, utilisateur_id)
        justificatif = session.get(JustificatifCaisse, id_justificatif)
        if justificatif is None or justificatif.Supprime:
            raise ErreurValidation(f"[VALIDATION] Le justificatif {id_justificatif} n'existe pas.")
        operation = session.get(OperationCaisse, justificatif.Id_Operation)
        if operation.Statut != "BROUILLON":
            raise ErreurValidation(
                "[VALIDATION] Un justificatif ne peut être supprimé qu'avant la validation de l'opération."
            )
        droits.exiger_createur_ou_manager(utilisateur, operation.Cree_Par)

        justificatif.Supprime = True
        session.commit()
        return {"succes": True, "message": message_succes(f"Justificatif '{justificatif.Nom_Fichier}' supprimé avec succès.")}
    except ErreurValidation:
        session.rollback()
        raise
    finally:
        session.close()
