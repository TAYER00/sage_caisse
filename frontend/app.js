// sage_caisse - Phases 6/7 - Interface React, écrite en JavaScript pur
// (React.createElement, pas de JSX/Babel/build - comme demandé). Inspirée
// de l'expérience Odoo 19 (hr_expense) sans en copier le code : barre
// supérieure, liste filtrable, fiche en sections, statuts colorés,
// workflow visible, notifications animées.
//
// Phase 7 : authentification réelle (remplace le sélecteur "Agir en tant
// que"), justificatifs (upload/téléchargement/suppression), export PDF réel.

import { api } from "./api.js";

const h = React.createElement;
const { useState, useEffect, useCallback } = React;

const LIBELLES_STATUT = { BROUILLON: "Brouillon", VALIDE: "Validé", COMPTABILISE: "Comptabilisé", ANNULE: "Annulé" };
const ETAPES_WORKFLOW = ["BROUILLON", "VALIDE", "COMPTABILISE"];

// --- Notifications animées ---------------------------------------------------

function ZoneToasts({ toasts, onFermer }) {
  return h(
    "div",
    { className: "zone-toasts" },
    toasts.map((t) =>
      h(
        "div",
        { key: t.id, className: `toast ${t.type}`, onClick: () => onFermer(t.id) },
        t.message
      )
    )
  );
}

function useToasts() {
  const [toasts, setToasts] = useState([]);
  const ajouter = useCallback((message, type = "succes") => {
    const id = Date.now() + Math.random();
    setToasts((liste) => [...liste, { id, message, type }]);
    setTimeout(() => setToasts((liste) => liste.filter((t) => t.id !== id)), 4000);
  }, []);
  const fermer = useCallback((id) => setToasts((liste) => liste.filter((t) => t.id !== id)), []);
  return { toasts, ajouter, fermer };
}

// --- Connexion (Phase 7) ---------------------------------------------------------

const CLE_LOCALSTORAGE_UTILISATEUR = "sage_caisse_utilisateur";

function EcranConnexion({ onConnecte, toasts }) {
  const [login, setLogin] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [enCours, setEnCours] = useState(false);

  const soumettre = async (e) => {
    e.preventDefault();
    setEnCours(true);
    try {
      const resultat = await api.seConnecter(login, motDePasse);
      toasts.ajouter(resultat.message, "succes");
      onConnecte(resultat.utilisateur);
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    } finally {
      setEnCours(false);
    }
  };

  return h(
    "div",
    { style: { display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" } },
    h(
      "form",
      { className: "fiche", style: { width: "320px" }, onSubmit: soumettre },
      h("h2", { style: { marginTop: 0, color: "var(--couleur-primaire)" } }, "sage_caisse"),
      h(
        "div",
        { className: "champ", style: { marginBottom: "12px" } },
        h("label", null, "Login"),
        h("input", { value: login, onChange: (e) => setLogin(e.target.value), autoFocus: true })
      ),
      h(
        "div",
        { className: "champ", style: { marginBottom: "16px" } },
        h("label", null, "Mot de passe"),
        h("input", { type: "password", value: motDePasse, onChange: (e) => setMotDePasse(e.target.value) })
      ),
      h("button", { type: "submit", className: "bouton", disabled: enCours, style: { width: "100%" } }, enCours ? "Connexion..." : "Se connecter")
    )
  );
}

// --- Barre supérieure ---------------------------------------------------------

function BarreHaut({ vue, onVue, utilisateurConnecte, onDeconnecter, lectureSeule, onBasculerMode }) {
  const onglets = [
    ["dashboard", "Tableau de bord"],
    ["operations", "Opérations"],
    ["caisses", "Caisses"],
  ];
  return h(
    "div",
    { className: "barre-haut" },
    h("span", { className: "titre" }, "sage_caisse"),
    h(
      "nav",
      null,
      onglets.map(([cle, libelle]) =>
        h("button", { key: cle, className: vue === cle ? "actif" : "", onClick: () => onVue(cle) }, libelle)
      )
    ),
    h(
      "div",
      { className: "droite" },
      h(
        "span",
        { className: `pastille-mode ${lectureSeule ? "lecture-seule" : "ecriture"}`, onClick: onBasculerMode, title: "Cliquer pour basculer (sans redémarrer le serveur)" },
        h("span", { className: "point" }),
        lectureSeule ? "Lecture seule" : "Écriture active"
      ),
      h(
        "span",
        { style: { fontWeight: 600 } },
        `${utilisateurConnecte.Nom_Complet} (${utilisateurConnecte.Role})`
      ),
      h("button", { className: "bouton secondaire", onClick: onDeconnecter }, "Se déconnecter")
    )
  );
}

// --- Tableau de bord -----------------------------------------------------------

function Dashboard({ caisses, operations, onNouvelleOperation }) {
  const comptes = { BROUILLON: 0, VALIDE: 0, COMPTABILISE: 0, ANNULE: 0 };
  operations.forEach((o) => { comptes[o.Statut] = (comptes[o.Statut] || 0) + 1; });

  return h(
    "div",
    null,
    h(
      "div",
      { className: "barre-action" },
      h("button", { className: "bouton", onClick: onNouvelleOperation }, "+ Nouvelle opération")
    ),
    h("div", { className: "groupe-titre" }, "Soldes des caisses"),
    h(
      "div",
      { className: "grille-cartes" },
      caisses.map((c) =>
        h(
          "div",
          { key: c.Id_Caisse, className: "carte" },
          h("div", { className: "valeur" }, `${Number(c.Solde_Actuel).toFixed(2)} ${c.Devise}`),
          h("div", { className: "libelle" }, c.Nom_Caisse)
        )
      ),
      caisses.length === 0 && h("div", { className: "message-vide" }, "Aucune caisse créée.")
    ),
    h("div", { className: "groupe-titre" }, "Opérations par statut"),
    h(
      "div",
      { className: "grille-cartes" },
      Object.entries(LIBELLES_STATUT).map(([code, libelle]) =>
        h(
          "div",
          { key: code, className: "carte" },
          h("div", { className: "valeur" }, comptes[code] || 0),
          h("div", { className: "libelle" }, libelle)
        )
      )
    )
  );
}

// --- Liste des opérations -------------------------------------------------------

function ListeOperations({ operations, caisses, utilisateurs, filtres, onFiltres, groupePar, onGroupePar, onOuvrir, onNouvelleOperation }) {
  const nomCaisse = (id) => (caisses.find((c) => c.Id_Caisse === id) || {}).Nom_Caisse || `Caisse ${id}`;
  const nomUtilisateur = (id) => (utilisateurs.find((u) => u.Id_Utilisateur === id) || {}).Nom_Complet || (id ? `#${id}` : "—");

  let groupes = { "Toutes les opérations": operations };
  if (groupePar === "caisse") {
    groupes = {};
    operations.forEach((o) => {
      const cle = nomCaisse(o.Id_Caisse);
      (groupes[cle] = groupes[cle] || []).push(o);
    });
  } else if (groupePar === "statut") {
    groupes = {};
    operations.forEach((o) => {
      const cle = LIBELLES_STATUT[o.Statut];
      (groupes[cle] = groupes[cle] || []).push(o);
    });
  } else if (groupePar === "beneficiaire") {
    groupes = {};
    operations.forEach((o) => {
      const cle = o.Beneficiaire || "Sans bénéficiaire";
      (groupes[cle] = groupes[cle] || []).push(o);
    });
  }

  return h(
    "div",
    null,
    h(
      "div",
      { className: "barre-action" },
      h("input", {
        placeholder: "Recherche rapide (référence, projet, observation)...",
        value: filtres.recherche || "",
        onChange: (e) => onFiltres({ ...filtres, recherche: e.target.value }),
      }),
      h(
        "select",
        { value: filtres.id_caisse || "", onChange: (e) => onFiltres({ ...filtres, id_caisse: e.target.value }) },
        h("option", { value: "" }, "Toutes les caisses"),
        caisses.map((c) => h("option", { key: c.Id_Caisse, value: c.Id_Caisse }, c.Nom_Caisse))
      ),
      h(
        "select",
        { value: filtres.statut || "", onChange: (e) => onFiltres({ ...filtres, statut: e.target.value }) },
        h("option", { value: "" }, "Tous les statuts"),
        Object.entries(LIBELLES_STATUT).map(([code, libelle]) => h("option", { key: code, value: code }, libelle))
      ),
      h(
        "select",
        { value: groupePar, onChange: (e) => onGroupePar(e.target.value) },
        h("option", { value: "" }, "Pas de regroupement"),
        h("option", { value: "caisse" }, "Regrouper par caisse"),
        h("option", { value: "statut" }, "Regrouper par statut"),
        h("option", { value: "beneficiaire" }, "Regrouper par bénéficiaire")
      ),
      h("button", { className: "bouton", onClick: onNouvelleOperation }, "+ Nouvelle opération")
    ),
    Object.entries(groupes).map(([titreGroupe, lignes]) =>
      h(
        React.Fragment,
        { key: titreGroupe },
        groupePar && h("div", { className: "groupe-titre" }, `${titreGroupe} (${lignes.length})`),
        h(
          "table",
          { className: "liste" },
          h(
            "thead",
            null,
            h(
              "tr",
              null,
              h("th", null, "Référence"),
              h("th", null, "Date"),
              h("th", null, "Caisse"),
              h("th", null, "Type"),
              h("th", null, "Projet"),
              h("th", null, "Responsable"),
              h("th", null, "Montant"),
              h("th", null, "Statut")
            )
          ),
          h(
            "tbody",
            null,
            lignes.map((o) =>
              h(
                "tr",
                { key: o.Id_Operation, onClick: () => onOuvrir(o.Id_Operation) },
                h("td", null, o.Reference),
                h("td", null, new Date(o.Date_Operation).toLocaleDateString("fr-FR")),
                h("td", null, nomCaisse(o.Id_Caisse)),
                h("td", null, o.Type_Operation),
                h("td", null, o.Projet || "—"),
                h("td", null, nomUtilisateur(o.Responsable)),
                h("td", null, `${Number(o.Montant).toFixed(2)} ${o.Devise}`),
                h("td", null, h("span", { className: `badge-statut ${o.Statut}` }, LIBELLES_STATUT[o.Statut]))
              )
            )
          )
        )
      )
    ),
    operations.length === 0 && h("div", { className: "message-vide" }, "Aucune opération ne correspond à ces filtres.")
  );
}

// --- Indicateur de progression du workflow ---------------------------------------

function ProgressionWorkflow({ statut }) {
  if (statut === "ANNULE") {
    return h("div", { className: "progression" }, h("span", { className: "etape atteinte ANNULE" }, "Annulé"));
  }
  const indexActuel = ETAPES_WORKFLOW.indexOf(statut);
  return h(
    "div",
    { className: "progression" },
    ETAPES_WORKFLOW.map((etape, i) =>
      h(
        React.Fragment,
        { key: etape },
        i > 0 && h("span", { className: "fleche" }, "→"),
        h("span", { className: `etape ${i <= indexActuel ? "atteinte " + etape : ""}` }, LIBELLES_STATUT[etape])
      )
    )
  );
}

// --- Formulaire de nouvelle opération ---------------------------------------------

function FormulaireOperation({ caisses, parametres, utilisateurCourant, onCree, onAnnulerSaisie, toasts }) {
  const [valeurs, setValeurs] = useState({
    type_operation: "DEPENSE", id_caisse: "", date_operation: new Date().toISOString().slice(0, 16),
    montant: "", sens_solde: "", id_motif: "", beneficiaire: "", responsable: "", societe: "",
    compte_financier: "", compte_analytique: "", devise: "EUR", projet: "", observation: "",
  });
  const maj = (champ) => (e) => setValeurs({ ...valeurs, [champ]: e.target.value });

  const soumettre = async (e) => {
    e.preventDefault();
    if (!valeurs.id_caisse) { toasts.ajouter("Veuillez sélectionner une caisse.", "erreur"); return; }
    if (!valeurs.montant || Number(valeurs.montant) <= 0) { toasts.ajouter("Le montant doit être supérieur à zéro.", "erreur"); return; }
    if (valeurs.type_operation === "REMBOURSEMENT" && !valeurs.sens_solde) {
      toasts.ajouter("Pour un remboursement, précisez s'il augmente ou diminue le solde.", "erreur");
      return;
    }
    try {
      const corps = {
        type_operation: valeurs.type_operation, id_caisse: Number(valeurs.id_caisse),
        date_operation: valeurs.date_operation, montant: Number(valeurs.montant), cree_par: utilisateurCourant.Id_Utilisateur,
        sens_solde: valeurs.sens_solde || null, id_motif: valeurs.id_motif ? Number(valeurs.id_motif) : null,
        beneficiaire: valeurs.beneficiaire || null, responsable: valeurs.responsable ? Number(valeurs.responsable) : null,
        societe: valeurs.societe || null, compte_financier: valeurs.compte_financier || null,
        compte_analytique: valeurs.compte_analytique || null, devise: valeurs.devise, projet: valeurs.projet || null,
        observation: valeurs.observation || null,
      };
      const resultat = await api.creerOperation(corps);
      toasts.ajouter(resultat.message, "succes");
      onCree();
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    }
  };

  return h(
    "form",
    { className: "fiche", onSubmit: soumettre },
    h(
      "div",
      { className: "section" },
      h("h3", null, "Informations générales"),
      h(
        "div",
        { className: "ligne-champs" },
        h(
          "div",
          { className: "champ" },
          h("label", null, "Type d'opération"),
          h(
            "select",
            { value: valeurs.type_operation, onChange: maj("type_operation") },
            h("option", { value: "ALIMENTATION" }, "Alimentation"),
            h("option", { value: "DEPENSE" }, "Dépense"),
            h("option", { value: "REMBOURSEMENT" }, "Remboursement")
          )
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Date"),
          h("input", { type: "datetime-local", value: valeurs.date_operation, onChange: maj("date_operation") })
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Caisse *"),
          h(
            "select",
            { value: valeurs.id_caisse, onChange: maj("id_caisse") },
            h("option", { value: "" }, "— Sélectionner —"),
            caisses.map((c) => h("option", { key: c.Id_Caisse, value: c.Id_Caisse }, c.Nom_Caisse))
          )
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Société"),
          h("input", { value: valeurs.societe, onChange: maj("societe") })
        )
      )
    ),
    valeurs.type_operation === "REMBOURSEMENT" &&
      h(
        "div",
        { className: "section" },
        h("h3", null, "Sens du remboursement (obligatoire - jamais déduit automatiquement)"),
        h(
          "div",
          { className: "ligne-champs" },
          h(
            "div",
            { className: "champ" },
            h("label", null, "Ce remboursement..."),
            h(
              "select",
              { value: valeurs.sens_solde, onChange: maj("sens_solde") },
              h("option", { value: "" }, "— À préciser —"),
              h("option", { value: "ENTREE" }, "Augmente le solde de la caisse"),
              h("option", { value: "SORTIE" }, "Diminue le solde de la caisse")
            )
          )
        )
      ),
    h(
      "div",
      { className: "section" },
      h("h3", null, "Informations financières"),
      h(
        "div",
        { className: "ligne-champs" },
        h(
          "div",
          { className: "champ" },
          h("label", null, "Montant *"),
          h("input", { type: "number", step: "0.01", value: valeurs.montant, onChange: maj("montant") })
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Devise"),
          h("input", { value: valeurs.devise, onChange: maj("devise") })
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Compte financier (Sage)"),
          h("input", { value: valeurs.compte_financier, onChange: maj("compte_financier"), placeholder: "ex: 5310" })
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Répartition analytique"),
          h("input", { value: valeurs.compte_analytique, onChange: maj("compte_analytique") })
        )
      )
    ),
    h(
      "div",
      { className: "section" },
      h("h3", null, "Informations opérationnelles"),
      h(
        "div",
        { className: "ligne-champs" },
        h(
          "div",
          { className: "champ" },
          h("label", null, "Motif"),
          h(
            "select",
            { value: valeurs.id_motif, onChange: maj("id_motif") },
            h("option", { value: "" }, "— Aucun —"),
            parametres.filter((p) => p.Categorie === "MOTIF").map((p) => h("option", { key: p.Id_Parametre, value: p.Id_Parametre }, p.Libelle))
          )
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Bénéficiaire (code tiers Sage)"),
          h("input", { value: valeurs.beneficiaire, onChange: maj("beneficiaire") })
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Responsable (code collaborateur Sage)"),
          h("input", { type: "number", value: valeurs.responsable, onChange: maj("responsable") })
        ),
        h(
          "div",
          { className: "champ" },
          h("label", null, "Projet"),
          h("input", { value: valeurs.projet, onChange: maj("projet") })
        )
      ),
      h(
        "div",
        { className: "champ", style: { marginTop: "12px" } },
        h("label", null, "Observation"),
        h("textarea", { rows: 3, value: valeurs.observation, onChange: maj("observation") })
      ),
      h(
        "div",
        { className: "champ", style: { marginTop: "12px", color: "#6b6b76", fontSize: "12px" } },
        "Justificatif : à ajouter une fois l'opération enregistrée, depuis sa fiche."
      )
    ),
    h(
      "div",
      { className: "barre-boutons" },
      h("button", { type: "submit", className: "bouton" }, "Enregistrer"),
      h("button", { type: "button", className: "bouton secondaire", onClick: onAnnulerSaisie }, "Annuler la saisie")
    )
  );
}

// --- Fiche détaillée d'une opération (workflow) -----------------------------------

function FicheOperation({ idOperation, utilisateurCourant, caisses, utilisateurs, onRetour, onChange, toasts }) {
  const [operation, setOperation] = useState(null);
  const [historique, setHistorique] = useState([]);
  const [validations, setValidations] = useState([]);
  const [justificatifs, setJustificatifs] = useState([]);
  const [commentaire, setCommentaire] = useState("");
  const refFichier = React.useRef(null);

  const charger = useCallback(async () => {
    const [o, h1, v1, j1] = await Promise.all([
      api.lireOperation(idOperation), api.listerHistorique(idOperation), api.listerValidations(idOperation),
      api.listerJustificatifs(idOperation),
    ]);
    setOperation(o.donnees);
    setHistorique(h1.resultats);
    setValidations(v1.resultats);
    setJustificatifs(j1.resultats);
  }, [idOperation]);

  useEffect(() => { charger(); }, [charger]);

  if (!operation) return h("div", { className: "chargement" }, "Chargement...");

  const nomUtilisateur = (id) => (utilisateurs.find((u) => u.Id_Utilisateur === id) || {}).Nom_Complet || (id ? `#${id}` : "—");
  const estCreateur = utilisateurCourant.Id_Utilisateur === operation.Cree_Par;
  const estManager = utilisateurCourant.Role === "MANAGER";

  const agir = async (action) => {
    try {
      let resultat;
      const corps = { utilisateur_id: utilisateurCourant.Id_Utilisateur, commentaire: commentaire || null };
      if (action === "valider") resultat = await api.validerOperation(idOperation, corps);
      if (action === "annuler") resultat = await api.annulerOperation(idOperation, corps);
      if (action === "comptabiliser") resultat = await api.comptabiliserOperation(idOperation, corps);
      if (action === "brouillon") resultat = await api.remettreEnBrouillon(idOperation, corps);
      if (action === "supprimer") resultat = await api.supprimerOperation(idOperation, utilisateurCourant.Id_Utilisateur);
      toasts.ajouter(resultat.message, action === "annuler" || action === "supprimer" ? "validation" : "succes");
      setCommentaire("");
      if (action === "supprimer") { onChange(); onRetour(); } else { await charger(); onChange(); }
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    }
  };

  const surChoixFichier = async (e) => {
    const fichier = e.target.files[0];
    if (!fichier) return;
    try {
      const resultat = await api.ajouterJustificatif(idOperation, utilisateurCourant.Id_Utilisateur, fichier);
      toasts.ajouter(resultat.message, "succes");
      await charger();
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    } finally {
      if (refFichier.current) refFichier.current.value = "";
    }
  };

  const supprimerJustificatif = async (id) => {
    try {
      const resultat = await api.supprimerJustificatif(id, utilisateurCourant.Id_Utilisateur);
      toasts.ajouter(resultat.message, "validation");
      await charger();
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    }
  };

  const imprimer = () => {
    window.open(api.urlPdfOperation(idOperation), "_blank");
  };

  return h(
    "div",
    null,
    h(
      "div",
      { className: "barre-action" },
      h("button", { className: "bouton secondaire", onClick: onRetour }, "← Retour à la liste")
    ),
    h("div", { className: "fiche" },
      h(
        "div",
        { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
        h("h2", { style: { margin: 0 } }, operation.Reference),
        h("span", { className: `badge-statut ${operation.Statut}` }, LIBELLES_STATUT[operation.Statut])
      ),
      h(ProgressionWorkflow, { statut: operation.Statut }),

      h(
        "div",
        { className: "section" },
        h("h3", null, "Informations générales"),
        h(
          "div",
          { className: "ligne-champs" },
          champLectureSeule("Type", operation.Type_Operation),
          champLectureSeule("Date", new Date(operation.Date_Operation).toLocaleString("fr-FR")),
          champLectureSeule("Caisse", (caisses.find((c) => c.Id_Caisse === operation.Id_Caisse) || {}).Nom_Caisse),
          champLectureSeule("Société", operation.Societe)
        )
      ),
      h(
        "div",
        { className: "section" },
        h("h3", null, "Informations financières"),
        h(
          "div",
          { className: "ligne-champs" },
          champLectureSeule("Montant", `${Number(operation.Montant).toFixed(2)} ${operation.Devise}`),
          champLectureSeule("Sens sur le solde", operation.Sens_Solde === "ENTREE" ? "Augmente le solde" : "Diminue le solde"),
          champLectureSeule("Compte financier", operation.Compte_Financier),
          champLectureSeule("Répartition analytique", operation.Compte_Analytique)
        )
      ),
      h(
        "div",
        { className: "section" },
        h("h3", null, "Informations opérationnelles"),
        h(
          "div",
          { className: "ligne-champs" },
          champLectureSeule("Bénéficiaire", operation.Beneficiaire),
          champLectureSeule("Responsable", nomUtilisateur(operation.Responsable)),
          champLectureSeule("Projet", operation.Projet),
          champLectureSeule("Observation", operation.Observation)
        )
      ),
      h(
        "div",
        { className: "section" },
        h("h3", null, "Informations de validation"),
        h(
          "div",
          { className: "ligne-champs" },
          champLectureSeule("Créé par", nomUtilisateur(operation.Cree_Par)),
          champLectureSeule("Validé par", operation.Valide_Par ? `${nomUtilisateur(operation.Valide_Par)} le ${new Date(operation.Date_Validation).toLocaleString("fr-FR")}` : "—"),
          champLectureSeule("Comptabilisé par", operation.Comptabilise_Par ? `${nomUtilisateur(operation.Comptabilise_Par)} le ${new Date(operation.Date_Comptabilisation).toLocaleString("fr-FR")}` : "—"),
          champLectureSeule("Référence comptable Sage", operation.Reference_Comptable_Sage || "— (aucune écriture Sage réelle)")
        )
      ),

      h(
        "div",
        { className: "champ", style: { marginBottom: "10px" } },
        h("label", null, "Commentaire (optionnel, associé à la prochaine action)"),
        h("input", { value: commentaire, onChange: (e) => setCommentaire(e.target.value) })
      ),
      h(
        "div",
        { className: "barre-boutons" },
        operation.Statut === "BROUILLON" && (estCreateur || estManager) &&
          h("button", { className: "bouton", onClick: () => agir("valider"), disabled: !estManager, title: !estManager ? "Réservé à un MANAGER" : "" }, "Valider"),
        operation.Statut === "BROUILLON" && (estCreateur || estManager) &&
          h("button", { className: "bouton danger", onClick: () => agir("annuler") }, "Annuler"),
        operation.Statut === "BROUILLON" && (estCreateur || estManager) &&
          h("button", { className: "bouton danger", onClick: () => agir("supprimer") }, "Supprimer"),
        operation.Statut === "VALIDE" &&
          h("button", { className: "bouton succes", onClick: () => agir("comptabiliser"), disabled: !estManager, title: !estManager ? "Réservé à un MANAGER" : "" }, "Comptabiliser"),
        operation.Statut === "VALIDE" &&
          h("button", { className: "bouton danger", onClick: () => agir("annuler"), disabled: !estManager, title: !estManager ? "Réservé à un MANAGER" : "" }, "Annuler"),
        operation.Statut === "VALIDE" &&
          h("button", { className: "bouton secondaire", onClick: () => agir("brouillon"), disabled: !estManager, title: !estManager ? "Réservé à un MANAGER" : "" }, "Remettre en brouillon"),
        h(
          "button",
          {
            className: "bouton secondaire",
            onClick: imprimer,
            disabled: !["VALIDE", "COMPTABILISE"].includes(operation.Statut),
            title: !["VALIDE", "COMPTABILISE"].includes(operation.Statut) ? "Désactivé tant que l'opération n'est pas Validée" : "",
          },
          "Imprimer (PDF)"
        )
      ),

      h(
        "div",
        { className: "journal" },
        h("h3", null, "Justificatifs"),
        justificatifs.length === 0 && h("div", { className: "message-vide" }, "Aucun justificatif pour l'instant."),
        justificatifs.map((j) =>
          h(
            "div",
            { key: j.Id_Justificatif, className: "journal-ligne", style: { display: "flex", justifyContent: "space-between", alignItems: "center" } },
            h(
              "span",
              null,
              h("a", { href: api.urlTelechargementJustificatif(j.Id_Justificatif), target: "_blank", rel: "noreferrer" }, j.Nom_Fichier),
              ` (${j.Type_Fichier}, ${(j.Taille_Octets / 1024).toFixed(0)} Ko)`,
              h("div", { className: "meta" }, new Date(j.Date_Ajout).toLocaleString("fr-FR"))
            ),
            operation.Statut === "BROUILLON" && (estCreateur || estManager) &&
              h("button", { className: "bouton secondaire", onClick: () => supprimerJustificatif(j.Id_Justificatif) }, "Supprimer")
          )
        ),
        operation.Statut !== "ANNULE" && operation.Statut !== "COMPTABILISE" &&
          h(
            "div",
            { style: { marginTop: "10px" } },
            h("input", { type: "file", accept: ".pdf,.jpg,.jpeg,.png", ref: refFichier, onChange: surChoixFichier }),
            h("div", { className: "meta", style: { marginTop: "4px" } }, "PDF, JPG ou PNG, 5 Mo maximum.")
          )
      ),

      h(
        "div",
        { className: "journal" },
        h("h3", null, "Historique des validations"),
        validations.length === 0 && h("div", { className: "message-vide" }, "Aucune action pour l'instant."),
        validations.map((v, i) =>
          h(
            "div",
            { key: i, className: "journal-ligne" },
            h("strong", null, v.Action), " — ", nomUtilisateur(v.Utilisateur),
            h("div", { className: "meta" }, `${new Date(v.Date_Action).toLocaleString("fr-FR")}${v.Commentaire ? " · " + v.Commentaire : ""}`)
          )
        )
      ),
      h(
        "div",
        { className: "journal" },
        h("h3", null, "Historique des modifications"),
        historique.length === 0 && h("div", { className: "message-vide" }, "Aucune modification pour l'instant."),
        historique.map((l, i) =>
          h(
            "div",
            { key: i, className: "journal-ligne" },
            h("strong", null, l.Champ_Modifie), `: "${l.Ancienne_Valeur ?? "—"}" → "${l.Nouvelle_Valeur ?? "—"}"`,
            h("div", { className: "meta" }, `${nomUtilisateur(l.Utilisateur)} · ${new Date(l.Date_Modification).toLocaleString("fr-FR")}`)
          )
        )
      )
    )
  );
}

function champLectureSeule(libelle, valeur) {
  return h(
    "div",
    { className: "champ" },
    h("label", null, libelle),
    h("div", null, valeur || valeur === 0 ? valeur : "—")
  );
}

// --- Gestion des caisses ------------------------------------------------------------

function VueCaisses({ caisses, onCree, toasts }) {
  const [valeurs, setValeurs] = useState({ code_caisse: "", nom_caisse: "", societe: "", solde_initial: "0", numero_caisse_sage: "" });
  const maj = (champ) => (e) => setValeurs({ ...valeurs, [champ]: e.target.value });

  const soumettre = async (e) => {
    e.preventDefault();
    try {
      const resultat = await api.creerCaisse({
        code_caisse: valeurs.code_caisse, nom_caisse: valeurs.nom_caisse, societe: valeurs.societe,
        solde_initial: Number(valeurs.solde_initial || 0),
        numero_caisse_sage: valeurs.numero_caisse_sage ? Number(valeurs.numero_caisse_sage) : null,
      });
      toasts.ajouter(resultat.message, "succes");
      setValeurs({ code_caisse: "", nom_caisse: "", societe: "", solde_initial: "0", numero_caisse_sage: "" });
      onCree();
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    }
  };

  return h(
    "div",
    null,
    h("div", { className: "groupe-titre" }, "Caisses existantes"),
    h(
      "table",
      { className: "liste" },
      h("thead", null, h("tr", null, h("th", null, "Code"), h("th", null, "Nom"), h("th", null, "Société"), h("th", null, "Solde"), h("th", null, "Statut"))),
      h(
        "tbody",
        null,
        caisses.map((c) =>
          h(
            "tr",
            { key: c.Id_Caisse },
            h("td", null, c.Code_Caisse), h("td", null, c.Nom_Caisse), h("td", null, c.Societe),
            h("td", null, `${Number(c.Solde_Actuel).toFixed(2)} ${c.Devise}`), h("td", null, c.Statut)
          )
        )
      )
    ),
    h("div", { className: "groupe-titre" }, "Nouvelle caisse"),
    h(
      "form",
      { className: "fiche", onSubmit: soumettre },
      h(
        "div",
        { className: "ligne-champs" },
        h("div", { className: "champ" }, h("label", null, "Code *"), h("input", { value: valeurs.code_caisse, onChange: maj("code_caisse") })),
        h("div", { className: "champ" }, h("label", null, "Nom *"), h("input", { value: valeurs.nom_caisse, onChange: maj("nom_caisse") })),
        h("div", { className: "champ" }, h("label", null, "Société *"), h("input", { value: valeurs.societe, onChange: maj("societe") })),
        h("div", { className: "champ" }, h("label", null, "Solde initial"), h("input", { type: "number", step: "0.01", value: valeurs.solde_initial, onChange: maj("solde_initial") })),
        h("div", { className: "champ" }, h("label", null, "N° caisse Sage (optionnel)"), h("input", { type: "number", value: valeurs.numero_caisse_sage, onChange: maj("numero_caisse_sage") }))
      ),
      h("div", { className: "barre-boutons" }, h("button", { type: "submit", className: "bouton" }, "Créer la caisse"))
    )
  );
}

// --- Application racine --------------------------------------------------------------

function App() {
  const toasts = useToasts();
  const [vue, setVue] = useState("dashboard");
  const [idOperationOuverte, setIdOperationOuverte] = useState(null);
  const [caisses, setCaisses] = useState([]);
  const [utilisateurs, setUtilisateurs] = useState([]);
  const [parametres, setParametres] = useState([]);
  const [operations, setOperations] = useState([]);
  const [filtres, setFiltres] = useState({});
  const [groupePar, setGroupePar] = useState("");
  const [lectureSeule, setLectureSeule] = useState(true);
  const [chargementInitial, setChargementInitial] = useState(true);

  // Authentification (Phase 7) - persistée dans localStorage, propre à ce
  // navigateur (pas une vraie session serveur - suffisant pour ce projet,
  // voir 00_analyse pour les limites assumées).
  const [utilisateurConnecte, setUtilisateurConnecte] = useState(() => {
    try {
      const brut = localStorage.getItem(CLE_LOCALSTORAGE_UTILISATEUR);
      return brut ? JSON.parse(brut) : null;
    } catch (e) {
      return null;
    }
  });

  const seConnecter = (utilisateur) => {
    setUtilisateurConnecte(utilisateur);
    try { localStorage.setItem(CLE_LOCALSTORAGE_UTILISATEUR, JSON.stringify(utilisateur)); } catch (e) { /* navigation privée, tant pis */ }
  };
  const seDeconnecter = () => {
    setUtilisateurConnecte(null);
    try { localStorage.removeItem(CLE_LOCALSTORAGE_UTILISATEUR); } catch (e) { /* ignoré */ }
  };

  const rafraichirReferentiels = useCallback(async () => {
    const [c, u, p, m] = await Promise.all([
      api.listerCaisses(), api.listerUtilisateurs(), api.listerParametres(), api.lireModeEcriture(),
    ]);
    setCaisses(c.resultats); setUtilisateurs(u.resultats); setParametres(p.resultats); setLectureSeule(m.lecture_seule);
  }, []);

  const rafraichirOperations = useCallback(async () => {
    const r = await api.listerOperations(filtres);
    setOperations(r.resultats);
  }, [filtres]);

  useEffect(() => {
    (async () => {
      try {
        await rafraichirReferentiels();
      } catch (err) {
        toasts.ajouter("Impossible de contacter le serveur API (" + err.message + "). Vérifiez qu'il est démarré sur 127.0.0.1:8000.", "erreur");
      } finally {
        setChargementInitial(false);
      }
    })();
  }, []);

  useEffect(() => { if (!chargementInitial) rafraichirOperations(); }, [rafraichirOperations, chargementInitial]);

  const basculerMode = async () => {
    try {
      const resultat = await api.modifierModeEcriture(lectureSeule); // on demande l'inverse de l'état actuel
      setLectureSeule(resultat.lecture_seule);
      toasts.ajouter(resultat.lecture_seule ? "Mode lecture seule activé." : "Écriture activée.", "succes");
    } catch (err) {
      toasts.ajouter(err.message, "erreur");
    }
  };

  if (!utilisateurConnecte) {
    return h(
      React.Fragment,
      null,
      h(EcranConnexion, { onConnecte: seConnecter, toasts }),
      h(ZoneToasts, { toasts: toasts.toasts, onFermer: toasts.fermer })
    );
  }

  if (chargementInitial) return h("div", { className: "chargement" }, "Chargement de sage_caisse...");

  let contenu;
  if (idOperationOuverte) {
    contenu = h(FicheOperation, {
      idOperation: idOperationOuverte, utilisateurCourant: utilisateurConnecte, caisses, utilisateurs,
      onRetour: () => setIdOperationOuverte(null),
      onChange: () => { rafraichirOperations(); rafraichirReferentiels(); },
      toasts,
    });
  } else if (vue === "dashboard") {
    contenu = h(Dashboard, { caisses, operations, onNouvelleOperation: () => setVue("nouvelle-operation") });
  } else if (vue === "nouvelle-operation") {
    contenu = h(FormulaireOperation, {
      caisses, parametres, utilisateurCourant: utilisateurConnecte,
      onCree: () => { setVue("operations"); rafraichirOperations(); },
      onAnnulerSaisie: () => setVue("operations"),
      toasts,
    });
  } else if (vue === "operations") {
    contenu = h(ListeOperations, {
      operations, caisses, utilisateurs, filtres, onFiltres: setFiltres, groupePar, onGroupePar: setGroupePar,
      onOuvrir: setIdOperationOuverte, onNouvelleOperation: () => setVue("nouvelle-operation"),
    });
  } else if (vue === "caisses") {
    contenu = h(VueCaisses, { caisses, onCree: rafraichirReferentiels, toasts });
  }

  return h(
    React.Fragment,
    null,
    h(BarreHaut, {
      vue: idOperationOuverte ? "operations" : vue,
      onVue: (v) => { setIdOperationOuverte(null); setVue(v); },
      utilisateurConnecte, onDeconnecter: seDeconnecter,
      lectureSeule, onBasculerMode: basculerMode,
    }),
    h("div", { className: "conteneur" }, contenu),
    h(ZoneToasts, { toasts: toasts.toasts, onFermer: toasts.fermer })
  );
}

ReactDOM.createRoot(document.getElementById("racine")).render(h(App));
