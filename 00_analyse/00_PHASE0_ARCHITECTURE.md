# PHASE 0 — Analyse du projet et architecture proposée (sage_caisse)

> Conformément au prompt : cette phase ne développe **rien**. Aucune table créée, aucun fichier de code écrit, aucune connexion en écriture tentée. Uniquement de l'analyse et une proposition, en attente de votre validation avant la Phase 1.

## 1. Environnement examiné (vérifié réellement, pas supposé)

| Élément | Résultat vérifié |
|---|---|
| Python | `3.10.11` installé et fonctionnel |
| `pyodbc` | `5.3.0` déjà installé |
| `python-dotenv` | `1.2.3` déjà installé |
| `pytest` | `9.1.1` déjà installé |
| `fastapi` | `0.141.1` déjà installé |
| `uvicorn` | `0.53.0` déjà installé |
| `pydantic` | `2.13.5` déjà installé |
| `sqlalchemy` | **non installé** |
| `alembic` | **non installé** |
| Driver ODBC SQL Server | `ODBC Driver 18 for SQL Server` présent (confirmé plus tôt sur ce poste, 32 et 64 bits) |
| MCP SQL Server (`bijou-readonly`) | **Connexion testée et réussie** à l'instant : serveur `DESKTOP-6BAJCDP\SAGE`, base `BIJOU`, SQL Server 2019 Standard Edition, lecture seule confirmée |

Conclusion : l'environnement a déjà presque tout ce qu'il faut. Il manquera seulement `SQLAlchemy` (et éventuellement `alembic` pour les migrations) au moment de la Phase 4 - pas installés maintenant, conformément à la règle "ne pas installer de dépendances inutiles" pour une phase qui ne code pas encore.

## 2. Ce que nous savons déjà sur Sage côté données (réutilisé, pas redécouvert)

Le document `docs/analyse_detaillee_f_creglement.md` (déjà produit, lecture seule, vérifié avec de vraies requêtes) nous donne une longueur d'avance pour la Phase 2 :

- `F_CREGLEMENT` a **60 colonnes réelles**, clé métier `RG_No`, clé physique technique `cbMarq`.
- Une seule contrainte de clé étrangère réelle en base : `F_CREGLEMENT.cbCA_No → F_CAISSE.CA_No`. Toutes les autres relations (`F_COMPTET`, `F_COLLABORATEUR`, `F_ECRITUREC`, `F_JOURNAUX`, `F_COMPTEG`, `F_CAISSETOTAL`) sont documentées par Sage mais **non contraintes physiquement**.
- **`F_CREGLEMENT` contient 0 ligne** dans cette base `BIJOU` de test - point important pour la suite : nous travaillerons avec un échantillon vide tant qu'aucun règlement réel n'y est saisi.

## 3. Architecture technique proposée

### 3.1 Principe directeur : s'inspirer de `sage_to_shopify`, pas le copier

Le projet `sage_to_shopify` (déjà construit, testé, validé par 43 tests + un import réel) a établi un pattern qui a fait ses preuves sur ce même serveur Sage :

| Principe | Dans `sage_to_shopify` | Appliqué ici (`sage_caisse`) |
|---|---|---|
| Lecture Sage strictement séparée de l'écriture | `ConnexionSageLectureSeule` (aucune méthode d'écriture, refuse tout ce qui n'est pas `SELECT`) | Identique : `ConnexionSageLectureSeule` réutilisée à l'identique pour lire `F_CREGLEMENT`, `F_CAISSE`, `F_COMPTET`, etc. |
| Base applicative séparée, jamais mélangée avec Sage | Base dédiée `CONNECTEUR_SAGE_SHOPIFY`, compte dédié `db_owner` sur cette seule base | Nouvelle base dédiée (nom à valider, proposition : `SAGE_CAISSE_APP`), compte dédié séparé |
| Moteur CRUD générique piloté par un registre déclaratif | `objets_metier/gestion_crud.py` + `registre_entites.py` | **Oui, c'est ici que "insérer" devient possible** : CRUD complet (`creer`/`lire`/`modifier`/`supprimer`/`lister`) mais **uniquement sur nos propres tables** (`CAISSES`, `OPERATIONS_CAISSE`...), jamais sur les tables Sage |
| Messages `[SUCCES]`/`[ERREUR]`/`[VALIDATION]` en français | `gestion_erreurs/exceptions.py` | Identique, avec `message_sql_lisible()` déjà écrit et testé |
| Relecture de contrôle avant tout `[SUCCES]` | `_relire_avec_tentatives()` (3 essais) | Identique - particulièrement utile ici pour la validation d'opérations financières |
| Mode lecture seule flexible, basculable en mémoire | `config/configuration.py: definir_mode_lecture_seule()` | Identique, utile pour les tests avant d'activer l'écriture |

**Point essentiel à ne jamais perdre de vue** (rappel du prompt) : même avec ce pattern "insertion", **on n'insère/modifie/supprime jamais dans les tables Sage** (`F_CREGLEMENT` et consorts restent en lecture seule, sans exception). L'insertion concerne uniquement la future base applicative `sage_caisse` elle-même (`OPERATIONS_CAISSE`, `CAISSES`, etc.), qui n'existe pas encore et dont le schéma sera proposé en Phase 3 - pas avant.

### 3.2 Arborescence de projet proposée

```
sage_caisse/
├── 00_analyse/                      # Documents d'analyse (ce fichier, puis dictionnaire F_CREGLEMENT caisse, etc.)
├── config/
│   ├── __init__.py
│   └── configuration.py             # Lecture .env, mode lecture seule flexible (repris de sage_to_shopify)
├── connexion/
│   ├── __init__.py
│   ├── connexion_sage_lecture.py    # Lecture SEULE sur BIJOU (F_CREGLEMENT, F_CAISSE, F_COMPTET...)
│   └── connexion_app.py             # Lecture + écriture sur la base applicative sage_caisse (à créer en Phase 3)
├── objets_metier/
│   ├── __init__.py
│   ├── lecture_sage.py              # Fonctions de lecture des tables Sage utiles (jamais d'écriture)
│   ├── registre_entites.py          # Registre déclaratif des entités applicatives (Caisse, Opération...)
│   ├── validations.py               # Règles communes (solde suffisant, statut, droits...)
│   └── gestion_crud.py              # CRUD générique sur les tables applicatives
├── gestion_erreurs/
│   ├── __init__.py
│   └── exceptions.py                # Exceptions + messages [SUCCES]/[ERREUR]/[VALIDATION]
├── api/                             # Phase 4+ : endpoints FastAPI (vide pour l'instant)
├── tests/
│   ├── __init__.py
│   └── conftest.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Rien de ceci n'est créé à ce stade - c'est une proposition à valider.

### 3.3 Technologies retenues (avec justification)

| Choix | Pourquoi |
|---|---|
| **FastAPI** (déjà installé) | Recommandé par le prompt. Validation automatique via Pydantic, documentation interactive générée automatiquement (`/docs`), performant, et déjà présent sur ce poste - aucune installation inutile. |
| **Pydantic** (déjà installé, dépendance de FastAPI) | Validation des données d'entrée (ex. "le montant doit être supérieur à zéro") directement au niveau des schémas API, avant même d'atteindre la logique métier. |
| **pyodbc** (déjà installé, déjà validé sur ce serveur) | Pour la lecture de Sage - **pas d'ORM côté Sage**. Les tables Sage ont des conventions propres (`cb*`, clés composites, pas de vraies FK) qui ne se prêtent pas bien à un ORM, et un ORM pourrait créer une tentation d'écrire dans Sage par accident. On garde le pattern `sage_to_shopify` : SQL explicite, lecture seule stricte. |
| **SQLAlchemy** (à installer en Phase 4, pas avant) | Pour la base applicative *uniquement* (`sage_caisse`, pas Sage) - plus adapté qu'un CRUD SQL manuel pour un schéma qui va évoluer (caisses, opérations, justificatifs, historique, validations). |
| **Alembic** (à évaluer en Phase 3/4) | Pour versionner les migrations du schéma applicatif si SQLAlchemy est retenu - à confirmer avec vous avant installation. |
| **React** (Phase 6, pas avant) | Recommandé par le prompt pour l'UX inspirée d'Odoo 19 (hr_expense) - pas de décision à prendre maintenant. |

### 3.4 Plan de tests (Phase 1, détaillé dans le prompt)

Les 5 tests demandés pour la Phase 1, et comment ils seront réalisés concrètement :

| Test | Méthode prévue |
|---|---|
| Connexion réussie | `ConnexionSageLectureSeule().tester_connexion()` avec de vrais identifiants `BIJOU_READONLY` |
| Connexion refusée | Même appel avec un mauvais mot de passe → doit lever `ErreurConnexion` avec message lisible |
| Table inexistante | `SELECT * FROM TABLE_QUI_N_EXISTE_PAS` → doit lever `ErreurConnexion` (erreur SQL Server propre, pas un plantage) |
| Requête incorrecte | SQL syntaxiquement invalide → même comportement |
| Lecture de données | `SELECT TOP 5 ... FROM F_CREGLEMENT` → fonctionne mais renvoie 0 ligne (table vide, voir section 2) ; on testera aussi sur `F_CAISSE` qui contient de vraies données |

### 3.5 Prérequis à installer (rien avant votre accord)

- Déjà présents : `pyodbc`, `python-dotenv`, `pytest`, `fastapi`, `uvicorn`, `pydantic`.
- À installer **seulement en Phase 4** (pas maintenant) : `sqlalchemy`, et `alembic` si vous validez son usage.
- Pas d'installation prévue pour la Phase 1 (connexion Sage) : tout est déjà disponible.

## 4. Risques techniques identifiés

| Risque | Détail | Mitigation |
|---|---|---|
| **Base de test vide** | `F_CREGLEMENT` et `F_REGLECH` ont 0 ligne dans `BIJOU` | Les tests de lecture de structure fonctionneront, mais les tests "sur données réelles" (ex. vérifier qu'un `CT_NumPayeur` existe bien dans `F_COMPTET`) seront limités. À signaler à chaque phase concernée plutôt que de le cacher. |
| **Création d'une nouvelle base applicative bloquée pour moi (agent)** | Lors du projet `sage_to_shopify`, la création de la base dédiée (`CREATE DATABASE`) et du login applicatif (`CREATE LOGIN`) ont été **bloquées par le mode automatique de l'outil** (raisons : fuite d'identifiants, octroi de permission, modification de ressource partagée) - même avec votre accord explicite en conversation. | **Vous avez dû exécuter ces scripts vous-même dans SSMS** la dernière fois. Il faudra probablement refaire pareil en Phase 3 pour `sage_caisse` : je préparerai le script SQL, vous l'exécuterez, je vérifierai ensuite en lecture. |
| **Aucune API Sage officielle vérifiée pour écrire des règlements de caisse** | Contrairement aux tiers (objets métier COM `CPTA.Base.18`, vérifiés dans `sage_Conex_CRUD`), aucune vérification n'a été faite pour un éventuel objet métier "caisse/règlement". Le prompt lui-même recommande de **ne pas** chercher à écrire dans Sage pour l'instant. | Mode autonome d'abord (recommandé par le prompt lui-même) : toutes les opérations vivent dans la base `sage_caisse`, Sage reste une simple source de lecture (listes de caisses, tiers, comptes...). La comptabilisation réelle sera étudiée **séparément**, plus tard, si demandé. |
| **Écart de version possible sur les champs Sage** | Déjà rencontré sur `F_CREGLEMENT` (60 colonnes réelles vs 62 attendues) | Toujours vérifier la structure réelle par requête avant de coder quoi que ce soit dessus - jamais supposer. |
| **Confusion entre validation interne et comptabilisation Sage** | Risque fonctionnel explicitement signalé dans le prompt | Statuts `Brouillon/Validé/Comptabilisé/Annulé` strictement gérés dans la base applicative ; `Comptabilisé` restera un statut *interne* tant que l'écriture réelle dans Sage n'est pas spécifiquement étudiée et autorisée. |

## 5. Rapport de fin de phase (Phase 0)

### A. Travail effectué
- Vérification réelle de l'environnement (Python, bibliothèques, driver ODBC, connexion MCP SQL Server).
- Relecture du document d'analyse `F_CREGLEMENT` déjà produit, pour éviter de refaire le travail en Phase 2.
- Proposition d'architecture complète (arborescence, technologies justifiées, plan de tests, risques).

### B. Modifications
- **Un seul fichier créé** : `sage_caisse/00_analyse/00_PHASE0_ARCHITECTURE.md` (ce document). Aucun code, aucune table, aucune connexion en écriture.

### C. Tests
| Test | Résultat |
|---|---|
| `mcp bijou-readonly test_connection` | ✅ Réussi (connexion réelle à BIJOU confirmée) |
| Vérification versions Python/bibliothèques | ✅ Confirmé par requête réelle (`pip show`) |

### D. Bugs
- Aucun à ce stade (phase d'analyse uniquement, rien exécuté qui puisse échouer côté métier).

### E. État
**Phase 0 terminée.**

### F. Reste à faire
- Votre validation de l'architecture proposée (ou ajustements).
- Phase 1 : écrire et tester réellement le module de connexion `ConnexionSageLectureSeule` adapté à ce projet, lire `F_CREGLEMENT` et `F_CAISSE`.

### G. Explication pédagogique
En Odoo, vous n'avez jamais besoin de "proposer une architecture avant de coder" de façon aussi formelle : le framework impose déjà sa structure (modèles Python ORM, vues XML, manifest). Sage 100 n'a pas d'ORM ni de framework applicatif pour nous - c'est une base SQL Server brute avec des conventions historiques (`cb*`, pas de vraies FK partout). D'où l'intérêt de documenter d'abord l'architecture : on construit nous-mêmes l'équivalent d'un "ORM maison", mais seulement sur **notre** base applicative, jamais sur Sage.

### H. Validation
**Validez-vous cette architecture pour passer à la Phase 1 (connexion SQL Server réelle à `F_CREGLEMENT`/`F_CAISSE`, avec les 5 tests demandés) ?** Je n'écrirai aucun code avant votre accord explicite.
