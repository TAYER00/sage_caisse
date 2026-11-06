# PHASE 8 — Durcissement production

Décision actée avec l'utilisateur : la session reste dans `localStorage`
côté frontend pour l'instant (pas de JWT/cookies dans cette phase — point
réouvrable plus tard si besoin). Cette phase couvre les 4 autres points
laissés ouverts en fin de Phase 7 : CORS, journalisation, séparation des
variables d'environnement, stratégie de sauvegarde.

## 1. CORS restreint

Avant : `allow_origins=["*"]` (tout site pouvait appeler l'API depuis un
navigateur). Maintenant : `ORIGINES_AUTORISEES` dans `.env`
(`http://127.0.0.1:5500,http://localhost:5500` en développement), lue par
`config/configuration.py` et injectée dans `CORSMiddleware`
(`api/main.py`). Méthodes et en-têtes autorisés limités à ce qui est
réellement utilisé (`GET/POST/PUT/DELETE`, `Content-Type`).

**Testé réellement** (serveur relancé, vraies requêtes `curl`) :
- Origine `http://127.0.0.1:5500` (le frontend) → en-tête
  `Access-Control-Allow-Origin` présent.
- Origine `http://evil-site.example` → en-tête absent (requête bloquée
  côté navigateur si elle venait d'un vrai site tiers).
- Les requêtes normales (sans vérification CORS, ex. `curl` direct ou
  Postman) continuent de fonctionner — CORS est une protection
  **navigateur**, pas une authentification.

En production : mettre dans `ORIGINES_AUTORISEES` l'URL réelle du
frontend déployé (jamais `*`).

## 2. Journalisation (`gestion_erreurs/journal.py`)

Un logger applicatif unique (`sage_caisse`), fichier `logs/sage_caisse.log`
avec rotation (1 Mo, 5 fichiers d'historique), non versionné (ajouté à
`.gitignore`).

Journalisé :
- Chaque requête HTTP : méthode, chemin, code de réponse, durée
  (middleware `journaliser_requete` dans `api/main.py`).
- Chaque erreur serveur (`ErreurSQL`/`ErreurConnexion`) avec son message.

**Jamais journalisé** : le corps des requêtes (mots de passe compris) -
le middleware ne lit que les métadonnées de la requête/réponse, jamais
`request.body()`.

**Testé réellement** : fichier `logs/sage_caisse.log` relu après plusieurs
appels réels, contient bien une ligne par requête avec le bon code HTTP et
une durée cohérente.

**Limite connue acceptée** : les tests automatisés (`pytest`) utilisant le
même `api/main.py` via `TestClient` écrivent aussi dans ce fichier - sans
impact fonctionnel (juste des lignes de test mêlées aux lignes réelles en
développement), pas corrigé pour ne pas ajouter de complexité non
demandée.

## 3. Variables d'environnement de production

Deux nouvelles variables dans `.env` / `.env.example` :
- `ENVIRONNEMENT` (`developpement` par défaut, `production` en prod) :
  si `production`, `/docs` et `/redoc` (documentation interactive de
  l'API) sont désactivés - ne pas exposer le détail des routes à un
  visiteur non authentifié.
- `ORIGINES_AUTORISEES` : voir section 1.

**Correction de sécurité au passage** : `.env.example` contenait encore le
vrai mot de passe SQL de lecture Sage (`SQL_READONLY_PASSWORD=...`) en
clair - copié-collé depuis `sage_to_shopify`. Contrairement à `.env`, ce
fichier n'est **pas** dans `.gitignore` (c'est un modèle, fait pour être
commité). Il n'avait pas encore été commité (vérifié via `git status`/
`git log`), mais corrigé immédiatement : toutes les valeurs réelles
remplacées par des champs vides.

**Testé réellement** : `/docs` reste accessible (`ENVIRONNEMENT` vaut
`developpement` dans le `.env` actuel) ; la logique de désactivation
(`docs_url=None` si `production`) est directe dans FastAPI, pas besoin
d'un test supplémentaire pour une condition aussi simple.

## 4. Sauvegardes de `SAGE_CAISSE_APP`

Pas d'automatisation mise en place (une sauvegarde/restauration de base
est une action d'administration serveur - hors du périmètre d'écriture de
ce projet, qui ne touche que via le compte applicatif `admine`, pas `sa`).
Recommandation à exécuter par vous (SSMS ou `sqlcmd`), à planifier en
tâche SQL Server Agent si vous voulez l'automatiser :

```sql
BACKUP DATABASE SAGE_CAISSE_APP
TO DISK = 'C:\Sauvegardes\SAGE_CAISSE_APP_FULL.bak'
WITH INIT, COMPRESSION, STATS = 10;
```

Fréquence conseillée : sauvegarde complète quotidienne (hors heures
d'activité), éventuellement des sauvegardes différentielles plus
fréquentes si le volume d'opérations devient important. `SAGE_CAISSE_APP`
ne contient aucune donnée Sage (lecture seule sur BIJOU) - seulement les
données propres à l'application (utilisateurs, caisses, opérations,
justificatifs sur disque dans `stockage_justificatifs/` - à inclure aussi
dans la sauvegarde globale du serveur, ce n'est pas un `BACKUP DATABASE`).

## 5. Tests automatisés

82/82 tests toujours réussis après les changements (aucun test ne
dépendait du comportement précédent de CORS ou de l'absence de
journalisation).

## 6. État

**Phase 8 terminée** sur le périmètre retenu (CORS, journalisation,
variables d'environnement, documentation des sauvegardes). Point
explicitement laissé ouvert, à la demande de l'utilisateur : remplacer
`localStorage` par une vraie session serveur (JWT ou cookies) - à
reprendre si besoin dans une phase ultérieure.
