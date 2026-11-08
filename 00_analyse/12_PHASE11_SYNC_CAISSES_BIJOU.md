# PHASE 11 — Synchronisation des caisses depuis BIJOU (implémentation)

Suite de `11_PHASE1_ANALYSE_SYNC_BIJOU.md` (analyse validée par l'utilisateur :
aucune écriture dans BIJOU, synchronisation en lecture uniquement).

## 1. Migration (`00_analyse/11_MIGRATION_SYNC_CAISSES.sql`)

Appliquée sur `SAGE_CAISSE_APP` (additive uniquement, aucune donnée supprimée) :
- `CAISSES.Derniere_Synchro_Sage` (DATETIME, NULL) - traçabilité.
- `CONSTRAINT UQ_Caisses_NumeroCaisseSage UNIQUE (Numero_Caisse_Sage)` - empêche
  qu'une même caisse Sage soit liée deux fois (NULL multiples toujours autorisés
  par SQL Server sous UNIQUE, donc les caisses sans lien Sage ne sont pas gênées).

`modeles/caisse.py` et `00_analyse/04_SCHEMA_SAGE_CAISSE.sql` mis à jour en
conséquence (pour qu'une réinstallation complète reparte avec le même schéma).

## 2. Lecture Sage (`objets_metier/lecture_sage.py: lister_caisses_sage`)

Nouvelle fonction (lecture seule) : lit **tout** `F_CAISSE`, jointe à
`F_DEPOT` pour résoudre la société réelle (`DE_No -> DE_Intitule`) - contrairement
à `lire_caisse_sage()` qui ne lit qu'une seule caisse par `CA_No`.

## 3. Service de synchronisation (`services/service_synchronisation_caisses.py`)

`synchroniser_caisses_depuis_sage(connexion_sage, utilisateur_id)` - upsert
idempotent, clé = `Numero_Caisse_Sage` :
- Caisse Sage inconnue → création (`Nom_Caisse` initial = `CA_Intitule`).
- Caisse Sage déjà liée → met à jour **uniquement** `Societe` et
  `Derniere_Synchro_Sage`. `Nom_Caisse` n'est **jamais** réécrit sur une
  caisse existante, ni `Solde_Initial`/`Solde_Actuel`/`Statut`, ni aucune
  `OPERATIONS_CAISSE` déjà liée.
- Caisse applicative sans `Numero_Caisse_Sage` → jamais touchée.
- Réservé aux MANAGER, soumis à `MODE_LECTURE_SEULE` comme toute écriture.

### Bug trouvé et corrigé en testant réellement

Première exécution réelle : la synchronisation a **réécrasé** `Nom_Caisse`
des 2 caisses existantes ("Caisse Principale Siège" → "Caisse 1 Bijou SA",
le libellé brut Sage). Ce n'était pas le comportement voulu - `Nom_Caisse`
devient une donnée propre à l'application dès sa création, et le prompt
demande explicitement de "ne pas écraser les données locales existantes".
Corrigé : `Nom_Caisse` n'est plus modifié sur une caisse déjà existante
(seul `Societe`, une donnée de référence Sage pure, est mis à jour). Les
2 noms ont été restaurés manuellement sur la vraie base avant la correction
du code, puis une resynchronisation réelle a confirmé qu'ils restent
désormais intacts.

## 4. API (`api/main.py`) et frontend (`frontend/app.js`, `api.js`)

`POST /caisses/synchroniser-depuis-sage` (corps : `{"utilisateur_id": int}`)
- ouvre une `ConnexionSageLectureSeule`, la teste, puis appelle le service.
Bouton "Synchroniser depuis Sage" dans `VueCaisses` (réservé MANAGER,
désactivé sinon) ; colonne "N° caisse Sage" ajoutée au tableau des caisses.

## 5. Tests

6 nouveaux tests avec une fausse connexion Sage (`FausseConnexionSage`,
aucun test automatisé ne touche la vraie base) : création des caisses
manquantes, idempotence (rejouer ne duplique rien), non-écrasement du nom
et du solde lors d'une resynchronisation, préservation d'une caisse sans
lien Sage, droits réservés au MANAGER. **101/101 tests réussis.**

## 6. Exécution réelle (avec accord explicite préalable)

Exécutée contre la vraie base (`BIJOU` lue, `SAGE_CAISSE_APP` écrite) :
- 1er passage : 2 caisses créées (`CA_No=3,4`, "Annexe Bijou"), 2 mises à
  jour (`Societe` corrigée de `"SOCIETE_ABC"` vers `"Bijou SA"`, la vraie
  valeur Sage).
- 2e passage (après correction du bug `Nom_Caisse`) : 0 créée, 4 mises à
  jour, noms choisis par l'application tous préservés, soldes inchangés
  (4814,50 € et 1120,00 €) - confirme l'idempotence en conditions réelles.
- Mode lecture seule restauré à la fin.

## 7. État

**Phase 11 terminée.** Les caisses applicatives reflètent maintenant les
4 vraies caisses Sage (`CA_No` 1 à 4), via une synchronisation répétable,
sans écriture dans BIJOU et sans perte de données locales.
