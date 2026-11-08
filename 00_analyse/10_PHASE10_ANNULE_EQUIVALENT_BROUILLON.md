# PHASE 10 — ANNULE devient équivalent à BROUILLON

Demande : "si l'opération est à l'état ANNULE ou BROUILLON : on peut la
modifier, la supprimer et la valider. Si l'état est VALIDE : seul un
MANAGER peut la remettre en brouillon."

## 1. Changement de règle

Avant (Phase 9) : ANNULE ne permettait que la suppression (ajoutée en
Phase 9) et la remise en brouillon - pas la modification ni la validation
directe (il fallait d'abord repasser par "remettre en brouillon").

Maintenant : `STATUTS_MODIFIABLES = ("BROUILLON", "ANNULE")` dans
`services/service_operations.py` - ces deux statuts se comportent de
façon rigoureusement identique :
- **Modifiable** (tous champs, créateur ou MANAGER) - `modifier_operation`.
- **Supprimable** (MANAGER uniquement) - `supprimer_operation` (déjà en Phase 9).
- **Validable directement** (MANAGER uniquement, `valider_operation`) -
  **nouveau** : plus besoin de repasser par "remettre en brouillon" pour
  revalider une opération annulée.

VALIDE reste strictement verrouillé (lecture seule, non supprimable) ;
sa seule porte de sortie reste "remettre en brouillon", réservée au
MANAGER (règle inchangée depuis la Phase 5/9).

## 2. Implémentation

- `valider_operation` : la vérification `operation.Statut != "BROUILLON"`
  devient `operation.Statut not in STATUTS_MODIFIABLES`. Le recalcul du
  solde (`recalculer_solde`, recalcul complet à partir de toutes les
  opérations VALIDE/COMPTABILISE) gère correctement la transition directe
  ANNULE → VALIDE sans code spécial.
- `modifier_operation` et `supprimer_operation` : remplacé leurs
  vérifications locales par la même constante partagée
  `STATUTS_MODIFIABLES`, pour éviter toute divergence future.

## 3. Frontend (`frontend/app.js`)

- `statutModifiable = ["BROUILLON", "ANNULE"].includes(operation.Statut)`
  remplace les conditions dispersées ; `peutModifier`, `peutSupprimer` et
  le nouveau `peutValider` s'appuient tous sur cette même valeur.
- Bouton "Valider" : visible désormais aussi depuis ANNULE (toujours
  désactivé si l'utilisateur n'est pas MANAGER).
- Le bandeau du mode édition mentionne "brouillon ou annulée".

## 4. Tests

4 nouveaux tests (modification d'une ANNULE, validation directe
ANNULE → VALIDE par un MANAGER avec recalcul de solde vérifié, refus pour
un USER, refus de revalider une COMPTABILISE). **96/96 tests réussis.**

## 5. Vérification en conditions réelles

Via l'API contre `SAGE_CAISSE_APP` : créée → annulée → modifiée (créateur,
toujours en ANNULE) → validation refusée pour un USER → validée
directement par un MANAGER depuis ANNULE → solde de la caisse mis à jour
correctement (-33 €). Nettoyage complet (remise en brouillon puis
suppression), solde et mode lecture seule restaurés à l'identique.

## 6. État

**Phase 10 terminée.**
