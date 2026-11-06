# PHASE 5 — Workflow, calcul des soldes et droits

## 1. Règles de droits retenues (déduites du prompt, à valider si besoin)

Le prompt donne les permissions **CRUD** par rôle, mais pas explicitement qui peut déclencher chaque action de workflow. Règle retenue, cohérente avec l'esprit du prompt ("Manager... peut intervenir sur les opérations selon les règles métier", "Remettre en brouillon, uniquement si autorisé") :

| Action | Qui peut le faire |
|---|---|
| Créer / modifier / supprimer un **BROUILLON** | Le créateur (USER ou MANAGER) |
| **Valider** (BROUILLON → VALIDE) | MANAGER uniquement |
| **Annuler un BROUILLON** | Le créateur ou un MANAGER |
| **Annuler une opération VALIDE** | MANAGER uniquement |
| **Remettre en brouillon** (VALIDE → BROUILLON) | MANAGER uniquement (explicite dans le prompt) |
| **Comptabiliser** (VALIDE → COMPTABILISE) | MANAGER uniquement |
| Modifier/supprimer une opération **VALIDE ou COMPTABILISE** | **Personne**, directement (règle explicite du prompt) |

Message d'erreur si refusé : `"[VALIDATION] Vous n'avez pas les droits nécessaires."` (repris mot pour mot de l'exemple du prompt).

## 2. Calcul du solde

Recalcul **complet** (pas incrémental) à chaque transition qui change l'ensemble des opérations "comptant" pour le solde - plus simple et plus sûr qu'un cumul progressif :

```
Solde_Actuel(caisse) = Solde_Initial
    + SUM(Montant) des opérations de cette caisse, Statut IN (VALIDE, COMPTABILISE), Sens_Solde = ENTREE
    - SUM(Montant) des opérations de cette caisse, Statut IN (VALIDE, COMPTABILISE), Sens_Solde = SORTIE
```

Les opérations `BROUILLON` et `ANNULE` ne comptent jamais. Recalcul déclenché après : Valider, Annuler (une opération qui était VALIDE), Comptabiliser, Remettre en brouillon.

## 3. Historique et traçabilité

- Chaque transition de statut écrit une ligne dans `VALIDATIONS_CAISSE` (Action, Utilisateur, Date).
- Chaque modification de champ sur un BROUILLON écrit une ligne dans `HISTORIQUE_CAISSE` par champ modifié (ancienne/nouvelle valeur) - complété en Phase 5 (la Phase 4 modifiait déjà les champs mais n'historisait pas encore).

## 4. Protection contre les doubles actions

Toute tentative de rejouer une transition déjà faite (ex. valider une opération déjà validée) est refusée avec un message clair ("Cette opération a déjà été validée." - repris de l'exemple du prompt), pas une erreur technique.
