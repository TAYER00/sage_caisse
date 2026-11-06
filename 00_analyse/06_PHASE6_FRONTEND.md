# PHASE 6 — Frontend (React, sans build, sans Odoo touché)

## 1. Choix techniques

- **React 18 en UMD** (chargé par `<script>` depuis un CDN, pas d'installation locale) + **JavaScript pur** (`React.createElement`, aucun JSX, aucun Babel) - conforme à votre demande "JS HTML CSS REACT" sans outil de build.
- Fichiers : `frontend/index.html`, `frontend/style.css`, `frontend/api.js` (client HTTP), `frontend/app.js` (composants).
- Aucun dossier Odoo n'a été modifié - consultation visuelle uniquement, pour s'inspirer de l'organisation d'une fiche de dépense (sections, statuts colorés, barre de progression), pas de copie de code.
- CORS activé côté API (développement local uniquement, à restreindre en Phase 8).

## 2. Ce qui est couvert dans cette phase

- Tableau de bord (soldes des caisses, compteurs par statut).
- Liste des opérations : recherche rapide, filtres (caisse/statut), regroupement (caisse/statut/bénéficiaire), tri par date, bouton "Nouvelle opération".
- Formulaire unique Alimentation/Dépense/Remboursement (sections Informations générales/financières/opérationnelles), avec le champ "sens du remboursement" qui n'apparaît que pour ce type - jamais déduit automatiquement.
- Fiche détaillée : 4 sections demandées, barre de progression du workflow, boutons d'action visibles/désactivés selon le statut ET le rôle de l'utilisateur courant, historique des validations et des modifications.
- Gestion des caisses (liste + création).
- Interrupteur `MODE_LECTURE_SEULE` directement dans la barre supérieure (répond enfin au point 1 de la Phase 4 historique : "interrupteur dans l'interface web, plus besoin d'éditer .env ni de redémarrer le serveur").
- Notifications animées (succès/erreur/validation), statuts colorés (gris/bleu/vert/rouge comme demandé).

## 3. Ce qui était reporté en Phase 6 — complété en Phase 7

- **Justificatifs (upload de fichiers)** : ✅ fait en Phase 7 (`services/service_justificatifs.py`, stockage disque + métadonnées).
- **Export PDF** : ✅ fait en Phase 7 (`services/service_pdf.py`, reportlab).
- **Authentification réelle** (login/mot de passe) : ✅ fait en Phase 7 (`POST /auth/connexion`, écran de connexion dédié), remplace le sélecteur "Agir en tant que...".

Voir `07_PHASE7_TESTS_INTEGRATION.md` pour le détail.

## 3bis. Toujours hors périmètre

- **Gestion des contacts / comptes financiers / répartition analytique** en tant qu'écrans dédiés avec CRUD complet : actuellement de simples champs texte dans le formulaire d'opération (pas encore de combobox alimentée par une vraie liste gérée en base applicative, en dehors des Motifs).

## 4. Test réel effectué (pas simulé)

Backend lancé sur `127.0.0.1:8001` (le port 8000 est déjà utilisé par `sage_Conex_CRUD` sur ce poste), frontend servi sur `127.0.0.1:5500`, testés avec un vrai navigateur (`agent-browser`) contre la vraie base `SAGE_CAISSE_APP` :

- Tableau de bord : soldes et compteurs corrects par rapport aux vraies données.
- Liste des opérations : les 4 opérations réelles affichées, triées, badges de statut corrects.
- Fiche détaillée (`DEP-2026-0001`, Comptabilisé) : sections, barre de progression, historique des validations et des modifications - tout correspond exactement aux données réelles en base.
- **Cycle d'écriture réel via l'interface** : bascule du mode lecture seule → écriture, sélection d'un utilisateur MANAGER réel (Sarah Mansouri), clic sur "Valider" (BROUILLON → VALIDÉ confirmé visuellement et en base), puis "Remettre en brouillon" pour restaurer l'opération `DEP-2026-0002` à son état d'origine - aucune donnée réelle laissée altérée.
- Mode remis en "Lecture seule" à la fin du test, navigateur fermé proprement.

## 5. Comment lancer

```
# Terminal 1 - API
cd sage_caisse
uvicorn api.main:app --reload --port 8001

# Terminal 2 - frontend (fichiers statiques)
cd sage_caisse/frontend
python -m http.server 5500
```
Puis ouvrir `http://127.0.0.1:5500/index.html`.
