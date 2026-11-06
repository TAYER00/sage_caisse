# PHASE 3 — Conception de la base métier applicative (`sage_caisse`)

> Rien n'est créé en base à ce stade - ce document et le script SQL associé (`04_SCHEMA_SAGE_CAISSE.sql`) sont une **proposition** en attente de votre validation, comme demandé par le prompt ("Attendre ma validation avant création"). Même règle que lors du projet `sage_to_shopify` : la création réelle (si vous validez) devra probablement être exécutée par vous dans SSMS, le mode automatique de l'outil ayant bloqué par le passé la création directe d'une base/d'un login par l'agent.

## 1. Principe directeur

- **8 tables**, pas 7 : j'ai ajouté `UTILISATEURS` (non listée dans le prompt) parce que la traçabilité explicitement demandée ("traçabilité du créateur", "traçabilité du validateur", "traçabilité du comptable", "authentification : login et mot de passe", "gestion des rôles") a besoin d'une table "qui" - sans elle, `VALIDATIONS_CAISSE` et `HISTORIQUE_CAISSE` n'auraient personne à référencer. Je le signale explicitement plutôt que de l'ajouter silencieusement.
- **Aucune contrainte de clé étrangère physique vers Sage** : les références à `F_COMPTET.CT_Num`, `F_COLLABORATEUR.CO_No`, `F_COMPTEG.CG_Num`, `F_CAISSE.CA_No` restent de simples colonnes (texte/entier), validées **au niveau applicatif** (en relisant Sage avant d'accepter la valeur) - exactement le pattern déjà utilisé dans `sage_to_shopify` pour `CORRESPONDANCE_ARTICLES`. SQL Server ne permet de toute façon pas de FK inter-bases fiables, et on ne veut surtout pas qu'une contrainte physique dépende de Sage.
- **Jamais de solde modifié directement** (règle explicite du prompt) : `CAISSES.Solde_Actuel` est une colonne de **cache**, recalculée par l'application à partir des opérations - jamais mise à jour "à la main" par un `UPDATE` isolé.
- **Statuts** : `BROUILLON / VALIDE / COMPTABILISE / ANNULE`, contraints par `CHECK`, transitions autorisées documentées en section 4 (pas enforcées par trigger SQL - ce sera la responsabilité du code métier en Phase 4/5, comme `valider_mode_ecriture_autorise()` dans `sage_to_shopify`).

## 2. Point ouvert résolu dans le schéma : le sens financier d'un remboursement

Le prompt l'interdit explicitement de deviner. Solution retenue dans le schéma : un champ **`Sens_Solde`** (`ENTREE`/`SORTIE`) séparé de `Type_Operation` :

| Type_Operation    | Sens_Solde                                      | Règle                                                                                                                       |
| ----------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `ALIMENTATION`  | `ENTREE`                                      | Toujours - imposé par l'application, pas de choix à la saisie                                                              |
| `DEPENSE`       | `SORTIE`                                      | Toujours - imposé par l'application                                                                                         |
| `REMBOURSEMENT` | **à choisir explicitement à la saisie** | L'utilisateur indique si ce remboursement précis augmente ou diminue le solde de la caisse - jamais déduit automatiquement |

**Cette règle devra être confirmée par vous avant la Phase 4** (c'est une règle métier, pas un détail technique).

## 3. Schéma des 8 tables (résumé - détail complet dans le script SQL)

| Table                         | Rôle                                                                                                    | Référence(s) Sage (non contraintes physiquement)                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `UTILISATEURS`              | Comptes applicatifs (login, rôle USER/MANAGER)                                                          | Aucune                                                                                                                  |
| `CAISSES`                   | Caisses gérées par l'application                                                                       | `F_CAISSE.CA_No` (optionnel, mapping), `F_COMPTEG.CG_Num`, `F_COLLABORATEUR.CO_No`                                |
| `PARAMETRES_CAISSE`         | Listes dynamiques (motifs, etc.), actif/inactif, jamais supprimées si utilisées                        | Aucune                                                                                                                  |
| `OPERATIONS_CAISSE`         | Table centrale : une ligne = une opération (alimentation/dépense/remboursement)                        | `F_COMPTET.CT_Num` (bénéficiaire), `F_COLLABORATEUR.CO_No` (responsable), `F_COMPTEG.CG_Num` (compte financier) |
| `JUSTIFICATIFS_CAISSE`      | Pièces jointes liées à une opération                                                                 | Aucune                                                                                                                  |
| `VALIDATIONS_CAISSE`        | Historique des actions de workflow (valider/annuler/comptabiliser)                                       | Aucune                                                                                                                  |
| `HISTORIQUE_CAISSE`         | Traçabilité champ par champ des modifications                                                          | Aucune                                                                                                                  |
| `CORRESPONDANCE_REGLEMENTS` | Lien futur entre une opération et un vrai règlement Sage (mode intégré, pas utilisé pour l'instant) | `F_CREGLEMENT.RG_No`, `F_ECRITUREC.EC_No`                                                                           |

Le champ **`Projet`** (`VARCHAR(100)`, optionnel) demandé précédemment est inclus dans `OPERATIONS_CAISSE`.

## 4. Règles de gestion et transitions de statut (documentées, pas encore codées - Phase 4/5)

```
BROUILLON  -> VALIDE          (action "Valider", utilisateur autorisé requis)
BROUILLON  -> ANNULE          (action "Annuler")
VALIDE     -> BROUILLON       (action "Remettre en brouillon", UNIQUEMENT si autorisé - rôle MANAGER)
VALIDE     -> COMPTABILISE    (action "Comptabiliser")
VALIDE     -> ANNULE          (action "Annuler" - CONFIRMÉ par vous le 2026-11-06)
COMPTABILISE -> (aucune transition directe)  -- toute correction passe par une opération de régularisation séparée, traçable
```

**Explication simple de la différence entre les deux actions possibles sur une opération Validée** (confirmée avec vous) :

| Action | Effet | Qui peut le faire |
|---|---|---|
| **Annuler** | Passe l'opération à `ANNULE` - définitif, elle sort du circuit, mais reste visible dans l'historique (jamais supprimée) | Selon les droits définis en Phase 5 |
| **Remettre en brouillon** | Repasse l'opération à `BROUILLON` - elle redevient modifiable, comme si elle n'avait jamais été validée | Uniquement un `MANAGER` (règle déjà prévue) |

Les deux actions existent et sont indépendantes : l'une n'empêche pas l'autre, elles partent toutes les deux du statut `VALIDE` mais vont vers des statuts différents (`ANNULE` vs `BROUILLON`).

Règle de solde (`CAISSES.Solde_Actuel`) :

```
Solde_Actuel = Solde_Initial
             + SUM(Montant) des opérations VALIDE ou COMPTABILISE avec Sens_Solde = 'ENTREE'
             - SUM(Montant) des opérations VALIDE ou COMPTABILISE avec Sens_Solde = 'SORTIE'
```

Les opérations `BROUILLON` et `ANNULE` n'impactent jamais le solde (à confirmer - alternative : une alimentation en brouillon pourrait être vue comme "en attente", à votre avis).

## 5. Script SQL proposé

Voir `04_SCHEMA_SAGE_CAISSE.sql` - **non exécuté**. Base cible proposée : `SAGE_CAISSE_APP` (nom à valider, séparée de Sage et de `CONNECTEUR_SAGE_SHOPIFY`).

## 6. Validation (2026-11-06)

**Les 5 points sont validés par vous** :

1. ✅ Nom de la base : `SAGE_CAISSE_APP`.
2. ✅ Table `UTILISATEURS` ajoutée.
3. ✅ Mécanisme `Sens_Solde` pour le remboursement.
4. ✅ Transitions de statut, y compris `VALIDE -> ANNULE` (confirmé) et `VALIDE -> BROUILLON` via "Remettre en brouillon" (deux actions distinctes, voir section 4).
5. ✅ Schéma des 8 tables.

Prochaine étape : préparer l'exécution réelle du script `04_SCHEMA_SAGE_CAISSE.sql`.

## 7. Vérification réelle après création (2026-11-06)

Vous avez exécuté le script. Vérifié en lecture seule côté serveur : **les 8 tables existent**, avec exactement le nombre de colonnes attendu (`CAISSES`=12, `CORRESPONDANCE_REGLEMENTS`=6, `HISTORIQUE_CAISSE`=7, `JUSTIFICATIFS_CAISSE`=9, `OPERATIONS_CAISSE`=26, `PARAMETRES_CAISSE`=6, `UTILISATEURS`=7, `VALIDATIONS_CAISSE`=6), les **13 contraintes de clé étrangère** du script sont bien présentes, et toutes les tables sont vides (0 ligne) comme attendu pour une base neuve.

**Phase 3 terminée et confirmée.**
