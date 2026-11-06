// sage_caisse - Phase 6/7 - client API très simple (fetch), sans dépendance.
// Deux formes d'erreur possibles dans "detail" :
//   - une chaîne déjà en français ([VALIDATION]/[ERREUR]) pour nos propres
//     exceptions (voir api/main.py, gestion centralisée des erreurs) ;
//   - un TABLEAU d'objets Pydantic (422) quand FastAPI rejette la requête
//     AVANT d'atteindre notre code (type invalide, champ obligatoire absent
//     du schéma...) - trouvé en testant réellement un formulaire vide
//     (Phase 7). Les deux formes sont normalisées ici en un seul message lisible.

const URL_API = "http://127.0.0.1:8001";

function messageLisible(donnees, statut) {
  const detail = donnees && donnees.detail;
  if (!detail) return `Erreur HTTP ${statut}`;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((erreur) => {
        const champ = Array.isArray(erreur.loc) ? erreur.loc[erreur.loc.length - 1] : "champ";
        return `${champ} : ${erreur.msg}`;
      })
      .join(" · ");
  }
  return `Erreur HTTP ${statut}`;
}

async function appeler(methode, chemin, corps) {
  const options = { method: methode, headers: { "Content-Type": "application/json" } };
  if (corps !== undefined) options.body = JSON.stringify(corps);
  const reponse = await fetch(URL_API + chemin, options);
  let donnees = null;
  try { donnees = await reponse.json(); } catch (e) { /* pas de corps JSON */ }
  if (!reponse.ok) {
    throw new Error(messageLisible(donnees, reponse.status));
  }
  return donnees;
}

export const api = {
  // Configuration
  lireModeEcriture: () => appeler("GET", "/configuration/mode-ecriture"),
  modifierModeEcriture: (actif) => appeler("PUT", "/configuration/mode-ecriture", { actif }),

  // Authentification (Phase 7)
  seConnecter: (login, mot_de_passe) => appeler("POST", "/auth/connexion", { login, mot_de_passe }),

  // Utilisateurs
  listerUtilisateurs: () => appeler("GET", "/utilisateurs"),
  creerUtilisateur: (donnees) => appeler("POST", "/utilisateurs", donnees),

  // Paramètres (motifs...)
  listerParametres: (categorie) => appeler("GET", `/parametres${categorie ? "?categorie=" + categorie : ""}`),
  creerParametre: (donnees) => appeler("POST", "/parametres", donnees),

  // Caisses
  listerCaisses: () => appeler("GET", "/caisses"),
  lireCaisse: (id) => appeler("GET", `/caisses/${id}`),
  creerCaisse: (donnees) => appeler("POST", "/caisses", donnees),
  recalculerSolde: (id) => appeler("POST", `/caisses/${id}/recalculer-solde`),

  // Opérations
  listerOperations: (filtres) => {
    const params = new URLSearchParams();
    Object.entries(filtres || {}).forEach(([cle, valeur]) => {
      if (valeur !== undefined && valeur !== null && valeur !== "") params.append(cle, valeur);
    });
    const suffixe = params.toString() ? "?" + params.toString() : "";
    return appeler("GET", "/operations" + suffixe);
  },
  lireOperation: (id) => appeler("GET", `/operations/${id}`),
  creerOperation: (donnees) => appeler("POST", "/operations", donnees),
  modifierOperation: (id, donnees) => appeler("PUT", `/operations/${id}`, donnees),
  supprimerOperation: (id, utilisateurId) => appeler("DELETE", `/operations/${id}?utilisateur_id=${utilisateurId}&confirmer=true`),
  validerOperation: (id, donnees) => appeler("POST", `/operations/${id}/valider`, donnees),
  annulerOperation: (id, donnees) => appeler("POST", `/operations/${id}/annuler`, donnees),
  comptabiliserOperation: (id, donnees) => appeler("POST", `/operations/${id}/comptabiliser`, donnees),
  remettreEnBrouillon: (id, donnees) => appeler("POST", `/operations/${id}/remettre-en-brouillon`, donnees),
  listerHistorique: (id) => appeler("GET", `/operations/${id}/historique`),
  listerValidations: (id) => appeler("GET", `/operations/${id}/validations`),

  // Justificatifs (Phase 7)
  listerJustificatifs: (idOperation) => appeler("GET", `/operations/${idOperation}/justificatifs`),
  ajouterJustificatif: async (idOperation, utilisateurId, fichier) => {
    const corps = new FormData();
    corps.append("fichier", fichier);
    const reponse = await fetch(
      `${URL_API}/operations/${idOperation}/justificatifs?utilisateur_id=${utilisateurId}`,
      { method: "POST", body: corps }
    );
    let donnees = null;
    try { donnees = await reponse.json(); } catch (e) { /* pas de corps JSON */ }
    if (!reponse.ok) throw new Error(messageLisible(donnees, reponse.status));
    return donnees;
  },
  urlTelechargementJustificatif: (idJustificatif) => `${URL_API}/justificatifs/${idJustificatif}/telecharger`,
  supprimerJustificatif: (idJustificatif, utilisateurId) =>
    appeler("DELETE", `/justificatifs/${idJustificatif}?utilisateur_id=${utilisateurId}`),

  // Export PDF (Phase 7)
  urlPdfOperation: (idOperation) => `${URL_API}/operations/${idOperation}/pdf`,
};
