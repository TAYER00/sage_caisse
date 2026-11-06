"""
Export PDF d'une opération (Phase 7 - complète la section "Export PDF" du
prompt, reportée en Phase 6). Généré avec reportlab (pur Python, pas de
dépendance système comme wkhtmltopdf/weasyprint).

Règle du prompt : le bouton d'impression reste désactivé tant que
l'opération n'est pas Validée - appliqué ici aussi, pas seulement côté
frontend (défense en profondeur : un appel direct à l'API doit être
bloqué de la même façon qu'un clic sur un bouton désactivé).
"""

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from connexion.connexion_app import obtenir_session
from gestion_erreurs.exceptions import ErreurValidation
from modeles.caisse import Caisse
from modeles.operation import OperationCaisse
from modeles.parametre import ParametreCaisse
from modeles.utilisateur import Utilisateur

STATUTS_IMPRIMABLES = ("VALIDE", "COMPTABILISE")


def _nom_utilisateur(session, id_utilisateur):
    if id_utilisateur is None:
        return "—"
    utilisateur = session.get(Utilisateur, id_utilisateur)
    return utilisateur.Nom_Complet if utilisateur else f"#{id_utilisateur}"


def generer_pdf_operation(id_operation: int) -> bytes:
    """
    Objectif : générer un PDF récapitulatif d'une opération de caisse.

    Parametres : id_operation (int).

    Retour : contenu binaire du PDF (bytes).

    Validations : l'opération doit exister et être VALIDE ou COMPTABILISE
    (règle du prompt : jamais d'impression avant validation).

    Erreurs possibles : ErreurValidation.

    Exemple :
        generer_pdf_operation(2)
    """
    session = obtenir_session()
    try:
        operation = session.get(OperationCaisse, id_operation)
        if operation is None:
            raise ErreurValidation(f"[VALIDATION] L'opération {id_operation} n'existe pas.")
        if operation.Statut not in STATUTS_IMPRIMABLES:
            raise ErreurValidation(
                "[VALIDATION] L'impression n'est possible qu'à partir du statut Validé "
                f"(statut actuel : '{operation.Statut}')."
            )

        caisse = session.get(Caisse, operation.Id_Caisse)
        motif = session.get(ParametreCaisse, operation.Id_Motif) if operation.Id_Motif else None

        tampon = BytesIO()
        pdf = canvas.Canvas(tampon, pagesize=A4)
        largeur, hauteur = A4
        marge = 20 * mm
        y = hauteur - marge

        def ligne(texte, taille=10, gras=False, saut=7 * mm):
            nonlocal y
            pdf.setFont("Helvetica-Bold" if gras else "Helvetica", taille)
            pdf.drawString(marge, y, texte)
            y -= saut

        ligne("sage_caisse — Fiche d'opération", 16, gras=True, saut=10 * mm)
        ligne(f"Référence : {operation.Reference}", 12, gras=True)
        ligne(f"Statut : {operation.Statut}", 11, saut=10 * mm)

        ligne("Informations générales", 12, gras=True)
        ligne(f"Type : {operation.Type_Operation}")
        ligne(f"Date : {operation.Date_Operation.strftime('%d/%m/%Y %H:%M') if operation.Date_Operation else '—'}")
        ligne(f"Caisse : {caisse.Nom_Caisse if caisse else operation.Id_Caisse}")
        ligne(f"Société : {operation.Societe or '—'}", saut=10 * mm)

        ligne("Informations financières", 12, gras=True)
        ligne(f"Montant : {float(operation.Montant):.2f} {operation.Devise}")
        ligne(f"Sens sur le solde : {'Augmente le solde' if operation.Sens_Solde == 'ENTREE' else 'Diminue le solde'}")
        ligne(f"Compte financier : {operation.Compte_Financier or '—'}")
        ligne(f"Répartition analytique : {operation.Compte_Analytique or '—'}", saut=10 * mm)

        ligne("Informations opérationnelles", 12, gras=True)
        ligne(f"Motif : {motif.Libelle if motif else '—'}")
        ligne(f"Bénéficiaire : {operation.Beneficiaire or '—'}")
        ligne(f"Projet : {operation.Projet or '—'}")
        ligne(f"Observation : {operation.Observation or '—'}", saut=10 * mm)

        ligne("Informations de validation", 12, gras=True)
        ligne(f"Créé par : {_nom_utilisateur(session, operation.Cree_Par)}")
        if operation.Valide_Par:
            ligne(f"Validé par : {_nom_utilisateur(session, operation.Valide_Par)} le "
                  f"{operation.Date_Validation.strftime('%d/%m/%Y %H:%M') if operation.Date_Validation else ''}")
        if operation.Comptabilise_Par:
            ligne(f"Comptabilisé par : {_nom_utilisateur(session, operation.Comptabilise_Par)} le "
                  f"{operation.Date_Comptabilisation.strftime('%d/%m/%Y %H:%M') if operation.Date_Comptabilisation else ''}")
        ligne(f"Référence comptable Sage : {operation.Reference_Comptable_Sage or '— (aucune écriture Sage réelle)'}")

        pdf.showPage()
        pdf.save()
        return tampon.getvalue()
    finally:
        session.close()
