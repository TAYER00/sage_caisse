# sage_caisse — Application de gestion des caisses et dépenses (connectée à Sage 100)

Phases 1 à 11 terminées : connexion Sage en lecture seule, base applicative `SAGE_CAISSE_APP`, backend FastAPI complet (CRUD + workflow + soldes + droits + justificatifs + PDF + authentification), frontend React (sans build) avec édition complète d'une opération en brouillon, testé en conditions réelles, durci pour la production (CORS restreint, journalisation, variables d'environnement séparées). Historique complet dans `00_analyse/`.

## Structure

```
config/                  Configuration (.env), interrupteur MODE_LECTURE_SEULE
connexion/
  connexion_sage_lecture.py   Lecture SEULE sur Sage BIJOU (aucune methode d'ecriture)
  connexion_app.py             SQLAlchemy vers SAGE_CAISSE_APP (lecture + ecriture)
objets_metier/
  lecture_sage.py              Lecture Sage (F_CREGLEMENT, F_CAISSE, F_COMPTET, F_COMPTEG, F_COLLABORATEUR)
modeles/                       8 modeles SQLAlchemy (UTILISATEURS, CAISSES, OPERATIONS_CAISSE...)
services/
  droits.py                    Regles de droits + interrupteur lecture seule
  service_utilisateurs.py       CRUD + authentification (Phase 7)
  service_parametres.py / service_caisses.py / service_operations.py
  service_justificatifs.py      Upload/telechargement/suppression de fichiers (Phase 7)
  service_pdf.py                 Export PDF d'une operation (Phase 7)
  service_synchronisation_caisses.py   Sync caisses depuis BIJOU, lecture seule (Phase 11)
gestion_erreurs/
  exceptions.py                 Exceptions + messages [SUCCES]/[ERREUR]/[VALIDATION]
  journal.py                     Journalisation applicative (Phase 8)
api/
  main.py                       FastAPI (CRUD + workflow + configuration + auth + justificatifs + PDF + sync caisses)
frontend/
  index.html / style.css / api.js / app.js   Interface React (UMD, sans build), ecran de connexion
tests/                          101 tests (connexion Sage reelle + services + workflow + API + justificatifs + PDF + auth + sync)
stockage_justificatifs/         Fichiers uploades (non versionne, voir .gitignore)
00_analyse/                     Documents de chaque phase (architecture, schema, workflow, frontend, tests d'integration, sync BIJOU)
```

## Lancer

```
pip install -r requirements.txt

# Backend (port 8001 - le port 8000 est deja pris par sage_Conex_CRUD sur ce poste)
uvicorn api.main:app --reload --port 8001

# Frontend (fichiers statiques)
cd frontend && python -m http.server 5500
# puis ouvrir http://127.0.0.1:5500/index.html et se connecter (POST /utilisateurs pour creer un compte si besoin)
```

## Lancer les tests

```
python -m pytest tests/ -v
```

## Règles absolues

- Aucune écriture n'est possible sur Sage depuis ce projet - `ConnexionSageLectureSeule` n'expose aucune méthode d'écriture.
- La comptabilisation reste un statut **interne** : aucune écriture réelle dans Sage n'est effectuée (voir prompt, section "Distinction importante" - mode autonome).
- Le mode lecture seule (`MODE_LECTURE_SEULE` dans `.env`, ou l'interrupteur dans l'interface web) bloque toute écriture sur `SAGE_CAISSE_APP` - vérifié par `services/droits.py: verifier_ecriture_autorisee()` dans chaque fonction d'écriture.
- Un mot de passe n'est jamais stocké ni renvoyé en clair (hachage PBKDF2-SHA256, voir `services/securite.py`).
- CORS restreint aux origines déclarées dans `ORIGINES_AUTORISEES` (`.env`) - jamais `"*"` en production.
- Chaque requête et chaque erreur serveur est journalisée dans `logs/sage_caisse.log` (jamais le corps des requêtes - voir `gestion_erreurs/journal.py`).

- Modification/suppression/validation d'une opération : autorisées en BROUILLON ou ANNULE (équivalents), verrouillées dès VALIDE/COMPTABILISE ; suppression directe réservée EXCLUSIVEMENT aux MANAGER.
- Synchronisation des caisses depuis BIJOU (`POST /caisses/synchroniser-depuis-sage`, MANAGER uniquement) : lecture seule sur Sage, clé d'appariement `Numero_Caisse_Sage` (jamais le nom), idempotente, ne réécrase jamais `Nom_Caisse`/`Solde_Initial`/`Solde_Actuel`/`Statut` ni les opérations déjà liées.

## Reste à faire

Remplacer la session `localStorage` actuelle par une vraie session serveur (JWT ou cookies) - explicitement reporté par l'utilisateur en fin de Phase 8, à reprendre si besoin. Voir `00_analyse/08_PHASE8_PRODUCTION.md`, `00_analyse/09_PHASE9_MODIF_SUPPRESSION.md` et `00_analyse/12_PHASE11_SYNC_CAISSES_BIJOU.md`.
