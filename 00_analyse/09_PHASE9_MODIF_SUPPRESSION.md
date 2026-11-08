# PHASE 9 — Modification étendue, remise en brouillon, suppression réservée au MANAGER

Demande (`prmopt_3.txt`) :
1. Modification : tous les champs d'une opération en BROUILLON.
2. Remise en brouillon : aussi depuis ANNULE (pas seulement VALIDE).
3. Opération VALIDÉE : modification interdite, champs lecture seule.
4. Suppression directe : réservée EXCLUSIVEMENT aux MANAGER, pour BROUILLON ou ANNULE.
5. Règles appliquées côté frontend ET backend.

## 1. Analyse avant modification

- Le point 3 était déjà respecté côté backend (`modifier_operation` refusait
  tout sauf BROUILLON) - mais le frontend n'avait **aucun mode édition** :
  la fiche d'opération n'affichait que des champs en lecture seule, sans
  bouton "Modifier" nulle part. `PUT /operations/{id}` existait côté API
  et dans `api.js`, mais n'était jamais appelé.
- Le point 1 ("tous les champs") n'était que partiellement vrai : seuls
  Montant/Projet/Observation/Bénéficiaire/Responsable/Compte_Financier/
  Compte_Analytique étaient modifiables (`OperationModification`) -
  Type_Operation, Sens_Solde, Id_Caisse, Date_Operation, Société, Motif,
  Devise en étaient exclus.
- Le point 2 : `remettre_en_brouillon` n'acceptait que VALIDE.
- Le point 4 : `supprimer_operation` n'acceptait que BROUILLON, et
  autorisait le créateur (USER) OU un MANAGER - pas "exclusivement MANAGER".

## 2. Backend (`services/service_operations.py`, `api/schemas.py`)

- `modifier_operation` accepte maintenant tous les champs métier. Règle
  spéciale Type_Operation/Sens_Solde reprise à l'identique de
  `creer_operation` : le sens est imposé pour ALIMENTATION/DEPENSE (toute
  valeur fournie est ignorée), et doit être donné explicitement si le type
  devient REMBOURSEMENT (jamais déduit automatiquement). Changer
  `Id_Caisse` est vérifié (la caisse doit exister) - sans impact sur aucun
  solde tant que l'opération reste en BROUILLON (`recalculer_solde` ne
  compte que VALIDE/COMPTABILISE).
- `remettre_en_brouillon` accepte maintenant VALIDE **ou** ANNULE (toujours
  réservé au MANAGER). Le recalcul du solde n'est déclenché que si le
  statut précédent était VALIDE (une ANNULE n'était déjà plus comptée).
- `supprimer_operation` accepte maintenant BROUILLON **ou** ANNULE, et
  vérifie `exiger_role(utilisateur, ("MANAGER",))` au lieu de
  `exiger_createur_ou_manager` - le créateur seul (USER) ne peut plus
  supprimer, même sa propre opération.
- `OperationModification` (schéma Pydantic) et `vers_champs_sql()` étendus
  avec `type_operation`, `id_caisse`, `date_operation`, `sens_solde`,
  `id_motif`, `societe`, `devise`.

### Bug trouvé et corrigé en testant réellement

Première tentative de suppression contre la **vraie base** : `500
Internal Server Error`. Cause réelle (visible dans `logs/sage_caisse.log`
et le traceback) : `HISTORIQUE_CAISSE`, `VALIDATIONS_CAISSE` et
`JUSTIFICATIFS_CAISSE` référencent `OPERATIONS_CAISSE` par clé étrangère
**sans suppression en cascade** côté SQL Server - supprimer une opération
qui a un historique (quasiment toutes, dès qu'une action de workflow a eu
lieu) violait la contrainte. Invisible avec les tests `pytest` (SQLite en
mémoire n'impose pas les clés étrangères par défaut).

Corrigé dans `supprimer_operation` : les lignes dépendantes sont purgées
explicitement (même transaction) avant de supprimer l'opération, et le
dossier de justificatifs sur disque est supprimé après coup. Pas de
modification du schéma SQL Server (pas de `ON DELETE CASCADE` ajouté) -
correctif applicatif uniquement, plus sûr qu'une migration sur la base
partagée.

## 3. Frontend (`frontend/app.js`)

- Nouveau mode édition dans `FicheOperation` (bouton "Modifier", visible
  uniquement si `Statut === "BROUILLON"` et (créateur ou MANAGER)) : tous
  les champs deviennent des `<input>`/`<select>` (même structure que
  `FormulaireOperation`), avec "Enregistrer les modifications" /
  "Annuler la modification". En dehors de ce mode, tout reste strictement
  en lecture seule (point 3), y compris pour VALIDE/COMPTABILISE/ANNULE.
- Bouton "Supprimer" : condition changée de
  `(estCreateur || estManager)` à `estManager` seul, et visible pour
  BROUILLON **et** ANNULE (`peutSupprimer`).
- Bouton "Remettre en brouillon" : visible pour VALIDE **et** ANNULE
  (`["VALIDE","ANNULE"].includes(operation.Statut)`), toujours désactivé
  si non-MANAGER (comportement déjà existant, inchangé).

## 4. Tests automatisés

16 nouveaux tests (modification étendue, changement de type/sens,
caisse inexistante, suppression MANAGER-only sur BROUILLON/ANNULE/VALIDE,
remise en brouillon depuis ANNULE). **92/92 tests réussis.**

## 5. Vérification en conditions réelles

- Via l'API directement (`curl`) contre `SAGE_CAISSE_APP` : création,
  modification de tous les champs (type, caisse, montant, société,
  bénéficiaire, responsable, comptes, devise, projet, observation),
  blocage après validation, suppression refusée pour un USER créateur,
  remise en brouillon refusée pour un USER, acceptée pour un MANAGER.
- Via un **vrai navigateur** (`agent-browser`) : connexion USER, édition
  réelle d'une opération BROUILLON (bouton Modifier → champs éditables →
  Enregistrer), valeurs confirmées par relecture API ; connexion MANAGER,
  remise en brouillon d'une ANNULE puis suppression - boutons
  correctement affichés/masqués selon le rôle.
- Toutes les données de test créées pendant la vérification ont été
  supprimées ; soldes des caisses réelles revenus à leur valeur initiale
  (4814,50 € et 1000,00 €) ; mode lecture seule remis actif à la fin.

## 6. État

**Phase 9 terminée.** Les 5 points de `prmopt_3.txt` sont implémentés,
testés (unitaires + réels) et documentés.
