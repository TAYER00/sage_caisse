# PHASE 12 — Bénéficiaire/Responsable : combobox de noms réels (synchronisés depuis BIJOU)

Demande : remplacer les champs libres "Bénéficiaire (code tiers Sage)" et
"Responsable (code collaborateur Sage)" du formulaire d'opération par des
combobox de noms, ces données devant elles aussi être synchronisées
depuis BIJOU.

## 1. Nouvelles tables miroir (`TIERS_SAGE`, `COLLABORATEURS_SAGE`)

Migration additive (`00_analyse/13_MIGRATION_REFERENTIELS_SAGE.sql`),
appliquée sur `SAGE_CAISSE_APP`. Contrairement à `CAISSES`, ce sont des
**miroirs purs** de `F_COMPTET`/`F_COLLABORATEUR` : aucune donnée propre à
l'application, donc chaque synchronisation réécrit intégralement
`Intitule`/`Nom_Complet` sans distinction à préserver (pas de risque
d'écraser un choix utilisateur, contrairement au bug `Nom_Caisse` corrigé
en Phase 11).

## 2. Lecture Sage et synchronisation

`objets_metier/lecture_sage.py` : `lister_tiers_sage()` (F_COMPTET, 68
lignes réelles) et `lister_collaborateurs_sage()` (F_COLLABORATEUR, 11
lignes réelles). `services/service_synchronisation_referentiels.py` :
upsert par clé réelle Sage (`CT_Num`/`CO_No`, jamais le nom), réservé
MANAGER. Les lignes absentes du dernier flux Sage ne sont **jamais
supprimées automatiquement** (prudence - testé et documenté).

### Bug trouvé et corrigé en testant réellement

Premier essai réel : `[ERREUR] La table 'COLLABORATEURS_SAGE' n'a pas la
propriété d'identité`. Cause : SQLAlchemy traite par défaut une clé
primaire entière à une seule colonne comme une IDENTITY et tente un `SET
IDENTITY_INSERT` ; or `CO_No` est l'identifiant réel Sage, pas une
colonne auto-incrémentée côté SQL Server. Corrigé avec
`autoincrement=False` sur `CollaborateurSage.CO_No`. Invisible avec
SQLite (tests automatisés) - trouvé uniquement contre la vraie base.

## 3. API et frontend

`GET /referentiels/tiers`, `GET /referentiels/collaborateurs`,
`POST /referentiels/synchroniser-depuis-sage`. Le bouton "Synchroniser
depuis Sage" (`VueCaisses`) déclenche maintenant les deux synchronisations
(caisses + référentiels) en un seul clic.

`FormulaireOperation` et le mode édition de `FicheOperation` : les champs
"Bénéficiaire"/"Responsable" sont devenus des `<select>` (valeur = code
Sage réel, libellé = nom réel). Partout en lecture seule (fiche, liste des
opérations), le code est résolu en nom via les référentiels synchronisés
- `Responsable` est désormais correctement résolu comme un **collaborateur
Sage** (`F_COLLABORATEUR`), et non plus par erreur comme un utilisateur de
l'application (bug d'affichage pré-existant, corrigé au passage).

## 4. Tests et vérification réelle

6 nouveaux tests (fausse connexion Sage). **104/104 tests réussis.**
Synchronisation réelle exécutée : 68 tiers + 11 collaborateurs importés.
Vérifié dans un vrai navigateur : combobox peuplées de noms réels,
opération créée avec les bons codes (`Beneficiaire="ORANGE"`,
`Responsable=10`), affichage et mode édition résolvent correctement les
noms. Donnée de test nettoyée, mode lecture seule restauré.

## 5. État

**Phase 12 terminée.**
