"""
API REST (FastAPI) - Phase 4.

Gestion centralisée des erreurs : ErreurValidation -> HTTP 400, toute
autre erreur applicative (ErreurSQL/ErreurConnexion) -> HTTP 500, avec le
message français déjà formaté ([VALIDATION]/[ERREUR]) renvoyé tel quel au
client - jamais une trace Python brute.

Lancer : uvicorn api.main:app --reload --port 8001 (depuis le dossier
sage_caisse/) - port 8001 car le port 8000 est déjà utilisé par l'API du
projet sage_Conex_CRUD sur ce poste.
Documentation interactive générée automatiquement : /docs (désactivée si
ENVIRONNEMENT=production, voir config/configuration.py - Phase 8).
"""

import time

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from config.configuration import ENVIRONNEMENT, ORIGINES_AUTORISEES, definir_mode_lecture_seule, mode_lecture_seule_actif
from connexion.connexion_sage_lecture import ConnexionSageLectureSeule
from gestion_erreurs.exceptions import ErreurConnexion, ErreurSageCaisse, ErreurSQL, ErreurValidation
from gestion_erreurs.journal import obtenir_journal
from services import (
    service_caisses,
    service_justificatifs,
    service_operations,
    service_parametres,
    service_pdf,
    service_synchronisation_caisses,
    service_synchronisation_referentiels,
    service_utilisateurs,
)
from api.schemas import (
    ActionComptabilisation,
    ActionWorkflow,
    CaisseCreation,
    ConnexionUtilisateur,
    ModeEcritureModification,
    OperationCreation,
    OperationModification,
    ParametreCreation,
    ReinitialisationMotDePasse,
    SynchronisationDemandee,
    UtilisateurCreation,
)

journal = obtenir_journal()

app = FastAPI(
    title="sage_caisse",
    description="Gestion des caisses et des dépenses, connectée à Sage 100 en lecture seule.",
    version="0.8.0",
    docs_url="/docs" if ENVIRONNEMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONNEMENT != "production" else None,
)

# CORS restreint aux origines réelles du frontend (ORIGINES_AUTORISEES dans
# .env) - Phase 8, remplace le "*" ouvert des phases précédentes (dev only).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINES_AUTORISEES,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def journaliser_requete(request: Request, appel_suivant):
    """
    Journalise chaque requête (méthode, chemin, code, durée) - jamais le
    corps de la requête, pour ne jamais écrire un mot de passe en clair
    dans les logs (voir POST /auth/connexion, POST /utilisateurs...).
    """
    debut = time.monotonic()
    reponse = await appel_suivant(request)
    duree_ms = int((time.monotonic() - debut) * 1000)
    journal.info(f"{request.method} {request.url.path} -> {reponse.status_code} ({duree_ms} ms)")
    return reponse


@app.exception_handler(ErreurValidation)
async def gerer_erreur_validation(request, exc: ErreurValidation):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ErreurSQL)
@app.exception_handler(ErreurConnexion)
async def gerer_erreur_serveur(request, exc: ErreurSageCaisse):
    journal.error(f"{request.method} {request.url.path} : {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# --- Configuration (interrupteur lecture seule, sans .env ni redemarrage) ----

@app.get("/configuration/mode-ecriture")
def lire_mode_ecriture():
    return {"lecture_seule": mode_lecture_seule_actif()}


@app.put("/configuration/mode-ecriture")
def modifier_mode_ecriture(donnees: ModeEcritureModification):
    definir_mode_lecture_seule(not donnees.actif)
    return {"succes": True, "lecture_seule": mode_lecture_seule_actif()}


# --- Authentification (Phase 7) ----------------------------------------------

@app.post("/auth/connexion")
def se_connecter(donnees: ConnexionUtilisateur):
    return service_utilisateurs.authentifier(donnees.login, donnees.mot_de_passe)


# --- Utilisateurs ------------------------------------------------------------

@app.post("/utilisateurs")
def creer_utilisateur(donnees: UtilisateurCreation):
    return service_utilisateurs.creer_utilisateur(donnees.login, donnees.mot_de_passe, donnees.nom_complet, donnees.role)


@app.post("/utilisateurs/{id_utilisateur}/mot-de-passe")
def reinitialiser_mot_de_passe(id_utilisateur: int, donnees: ReinitialisationMotDePasse):
    return service_utilisateurs.reinitialiser_mot_de_passe(id_utilisateur, donnees.nouveau_mot_de_passe, donnees.utilisateur_id)


@app.get("/utilisateurs")
def lister_utilisateurs():
    return service_utilisateurs.lister_utilisateurs()


# --- Paramètres (listes dynamiques, ex. motifs) -----------------------------

@app.post("/parametres")
def creer_parametre(donnees: ParametreCreation):
    return service_parametres.creer_parametre(donnees.categorie, donnees.code, donnees.libelle)


@app.get("/parametres")
def lister_parametres(categorie: str | None = None):
    return service_parametres.lister_parametres(categorie)


@app.post("/parametres/{id_parametre}/desactiver")
def desactiver_parametre(id_parametre: int):
    return service_parametres.desactiver_parametre(id_parametre)


# --- Caisses -----------------------------------------------------------------

@app.post("/caisses")
def creer_caisse(donnees: CaisseCreation):
    return service_caisses.creer_caisse(
        donnees.code_caisse, donnees.nom_caisse, donnees.societe, donnees.solde_initial,
        donnees.numero_caisse_sage, donnees.compte_financier, donnees.responsable_caisse, donnees.devise,
    )


@app.get("/caisses")
def lister_caisses(actives_seulement: bool = False):
    return service_caisses.lister_caisses(actives_seulement)


@app.get("/caisses/{id_caisse}")
def lire_caisse(id_caisse: int):
    return service_caisses.lire_caisse(id_caisse)


@app.post("/caisses/synchroniser-depuis-sage")
def synchroniser_caisses_depuis_sage(donnees: SynchronisationDemandee):
    """Phase 11 (prompt_4.txt) - lecture seule sur BIJOU, écriture uniquement dans SAGE_CAISSE_APP."""
    connexion_sage = ConnexionSageLectureSeule()
    connexion_sage.tester_connexion()
    return service_synchronisation_caisses.synchroniser_caisses_depuis_sage(connexion_sage, donnees.utilisateur_id)


# --- Référentiels Sage : tiers, collaborateurs (Phase 12) ---------------------

@app.get("/referentiels/tiers")
def lister_tiers():
    return service_synchronisation_referentiels.lister_tiers()


@app.get("/referentiels/collaborateurs")
def lister_collaborateurs():
    return service_synchronisation_referentiels.lister_collaborateurs()


@app.post("/referentiels/synchroniser-depuis-sage")
def synchroniser_referentiels_depuis_sage(donnees: SynchronisationDemandee):
    """Phase 12 - lecture seule sur BIJOU (F_COMPTET, F_COLLABORATEUR), écriture uniquement dans SAGE_CAISSE_APP."""
    connexion_sage = ConnexionSageLectureSeule()
    connexion_sage.tester_connexion()
    return service_synchronisation_referentiels.synchroniser_referentiels_depuis_sage(connexion_sage, donnees.utilisateur_id)


# --- Opérations de caisse -----------------------------------------------------

@app.post("/operations")
def creer_operation(donnees: OperationCreation):
    return service_operations.creer_operation(
        type_operation=donnees.type_operation, id_caisse=donnees.id_caisse,
        date_operation=donnees.date_operation, montant=donnees.montant, cree_par=donnees.cree_par,
        sens_solde=donnees.sens_solde, id_motif=donnees.id_motif, beneficiaire=donnees.beneficiaire,
        responsable=donnees.responsable, societe=donnees.societe, compte_financier=donnees.compte_financier,
        compte_analytique=donnees.compte_analytique, devise=donnees.devise, projet=donnees.projet,
        observation=donnees.observation,
    )


@app.get("/operations")
def lister_operations(
    id_caisse: int | None = None,
    projet: str | None = None,
    responsable: int | None = None,
    statut: str | None = None,
    recherche: str | None = Query(default=None, description="Recherche libre sur référence/projet/observation"),
):
    return service_operations.lister_operations(id_caisse, projet, responsable, statut, recherche)


@app.get("/operations/{id_operation}")
def lire_operation(id_operation: int):
    return service_operations.lire_operation(id_operation)


@app.get("/operations/{id_operation}/historique")
def lister_historique_operation(id_operation: int):
    return service_operations.lister_historique(id_operation)


@app.get("/operations/{id_operation}/validations")
def lister_validations_operation(id_operation: int):
    return service_operations.lister_validations(id_operation)


@app.put("/operations/{id_operation}")
def modifier_operation(id_operation: int, donnees: OperationModification):
    return service_operations.modifier_operation(id_operation, donnees.utilisateur_id, **donnees.vers_champs_sql())


@app.delete("/operations/{id_operation}")
def supprimer_operation(id_operation: int, utilisateur_id: int, confirmer: bool = False):
    return service_operations.supprimer_operation(id_operation, utilisateur_id, confirmer)


# --- Workflow (Phase 5) -------------------------------------------------------

@app.post("/operations/{id_operation}/valider")
def valider_operation(id_operation: int, donnees: ActionWorkflow):
    return service_operations.valider_operation(id_operation, donnees.utilisateur_id, donnees.commentaire)


@app.post("/operations/{id_operation}/annuler")
def annuler_operation(id_operation: int, donnees: ActionWorkflow):
    return service_operations.annuler_operation(id_operation, donnees.utilisateur_id, donnees.commentaire)


@app.post("/operations/{id_operation}/comptabiliser")
def comptabiliser_operation(id_operation: int, donnees: ActionComptabilisation):
    return service_operations.comptabiliser_operation(
        id_operation, donnees.utilisateur_id, donnees.reference_comptable_sage, donnees.commentaire
    )


@app.post("/operations/{id_operation}/remettre-en-brouillon")
def remettre_en_brouillon(id_operation: int, donnees: ActionWorkflow):
    return service_operations.remettre_en_brouillon(id_operation, donnees.utilisateur_id, donnees.commentaire)


# --- Solde de caisse -----------------------------------------------------------

@app.post("/caisses/{id_caisse}/recalculer-solde")
def recalculer_solde(id_caisse: int):
    return service_caisses.recalculer_solde(id_caisse)


# --- Justificatifs (Phase 7) ---------------------------------------------------

@app.post("/operations/{id_operation}/justificatifs")
async def ajouter_justificatif(id_operation: int, utilisateur_id: int, fichier: UploadFile = File(...)):
    contenu = await fichier.read()
    return service_justificatifs.ajouter_justificatif(id_operation, fichier.filename, contenu, utilisateur_id)


@app.get("/operations/{id_operation}/justificatifs")
def lister_justificatifs(id_operation: int):
    return service_justificatifs.lister_justificatifs(id_operation)


@app.get("/justificatifs/{id_justificatif}/telecharger")
def telecharger_justificatif(id_justificatif: int):
    chemin, nom_fichier = service_justificatifs.lire_fichier_justificatif(id_justificatif)
    return FileResponse(path=chemin, filename=nom_fichier)


@app.delete("/justificatifs/{id_justificatif}")
def supprimer_justificatif(id_justificatif: int, utilisateur_id: int):
    return service_justificatifs.supprimer_justificatif(id_justificatif, utilisateur_id)


# --- Export PDF (Phase 7) -------------------------------------------------------

@app.get("/operations/{id_operation}/pdf")
def telecharger_pdf_operation(id_operation: int):
    contenu = service_pdf.generer_pdf_operation(id_operation)
    return Response(content=contenu, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="operation_{id_operation}.pdf"'
    })
