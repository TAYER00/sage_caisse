# PHASE 1 — Analyse (prompt_4.txt) : intégration des caisses BIJOU ↔ SAGE_CAISSE_APP

> Rédigé à partir d'une lecture réelle de BIJOU (lecture seule, `BIJOU_READONLY`, aucune écriture) et du code actuel (`modeles/caisse.py`, `services/service_caisses.py`, `objets_metier/lecture_sage.py`, `00_analyse/RAPPORT_CORRESPONDANCE_SAGE_CAISSE_APP_BIJOU.md`). Conformément à la demande, **aucune modification n'a été effectuée dans BIJOU** - cette analyse précède toute décision de développement.

## 1. Table BIJOU concernée : `F_CAISSE`

### 1.1 Structure réelle (28 colonnes, lues via `INFORMATION_SCHEMA.COLUMNS`)

| Colonne | Type | Nullable | Rôle |
|---|---|---|---|
| `CA_No` | int | - | **Clé de la caisse Sage** (déjà utilisée comme `Numero_Caisse_Sage` côté app) |
| `CA_Intitule` | varchar(35) | oui | Nom de la caisse |
| `cbCA_Intitule` | **varbinary(36)** | oui | Copie binaire de contrôle de `CA_Intitule` (voir section 3) |
| `DE_No` | int | **NON** | FK réelle → `F_DEPOT.DE_No` (le "dépôt" = en réalité la société/site) |
| `CO_No` | int | oui | Responsable de la caisse (`F_COLLABORATEUR.CO_No`), 0 = non renseigné |
| `cbCO_No` | int | oui | Contrôle binaire de `CO_No` |
| `CO_NoCaissier` | int | oui | Caissier assigné (`F_COLLABORATEUR.CO_No`), 0 = non renseigné |
| `cbCO_NoCaissier` | int | oui | Contrôle binaire de `CO_NoCaissier` |
| `CT_Num` | varchar(17) | **NON** | Tiers "client divers" par défaut (`F_COMPTET.CT_Num`) |
| `cbCT_Num` | varbinary(18) | oui | Contrôle binaire de `CT_Num` |
| `JO_Num` | varchar(7) | **NON** | Journal Sage (`F_JOURNAUX.JO_Num`) |
| `cbMarq`, `cbId`, `cbCreation`, `cbCreationUser`, `cbModification`, `cbReplication`, `cbFlag`, `cbProt`, `cbCreateur` | divers | - | **Métadonnées internes Sage** (horodatage, identifiant GUID, réplication) |
| `N_Comptoir`, `N_Clavier`, `CA_IdentifCaissier`, `CA_LignesAfficheur`, `CA_ColonnesAfficheur`, `CA_ImpTicket`, `CA_SaisieVendeur`, `CA_Souche` | smallint | oui | Paramètres de point de vente (écran, imprimante, clavier...) - sans rapport avec la gestion de caisse applicative |

**Clé étrangère réelle trouvée** (`get_foreign_keys`) : `FKA_F_CAISSE_DE_No` : `F_CAISSE.DE_No → F_DEPOT.DE_No`.

### 1.2 Données réelles actuelles (les 4 lignes existantes, intégralement lues)

| `CA_No` | `CA_Intitule` | `DE_No` (dépôt) | `CO_No` | `CO_NoCaissier` | `CT_Num` | `JO_Num` |
|---|---|---|---|---|---|---|
| 1 | Caisse 1 Bijou SA | 1 | 0 | 0 | COMPTOIR | CAIS |
| 2 | Caisse 2 Bijou SA | 1 | 0 | 0 | COMPTOIR | CAIS |
| 3 | Caisse 1 Annexe Bijou | 1 | 0 | 0 | COMPTOIR | CAIS |
| 4 | Caisse 2 Annexe Bijou | 1 | 0 | 0 | COMPTOIR | CAIS |

Tables liées, lues pour interpréter ces valeurs :
- `F_DEPOT` (2 lignes) : `DE_No=1` → **"Bijou SA"**, `DE_No=2` → **"Annexe Bijou SA"**. `DE_No` est donc la **société réelle** de la caisse, malgré son nom de colonne ("dépôt").
- `F_COMPTET` : `CT_Num='COMPTOIR'` → *"Client divers"* (`CT_Type=0`) - un tiers générique de point de vente, **identique pour les 4 caisses**, sans valeur différenciante à synchroniser.
- `F_COLLABORATEUR` : 3 collaborateurs réels flagués `CO_Caissier=1` → `CO_No` 4 (Dorine ECLAT), 8 (Eddy HAMAND), 10 (Tiffany PANDAN). **Aucun n'est actuellement assigné** à une caisse (`CO_No`/`CO_NoCaissier` valent 0 partout).

**Constat de données** (signalé, non corrigé - ce n'est pas mon rôle de modifier vos données sans accord) : les caisses 3 et 4 s'appellent *"Annexe Bijou"* mais ont `DE_No=1` ("Bijou SA"), pas `DE_No=2` - possible incohérence de saisie côté Sage, à vérifier de votre côté si c'est important pour vous.

## 2. Constat principal : **il n'y a rien à créer dans BIJOU**

Contrairement à l'hypothèse de départ ("préparer des requêtes SQL pour créer ou alimenter les données de caisse dans BIJOU"), les 4 caisses réelles existent déjà, intégralement renseignées sur tous les champs obligatoires (`DE_No`, `CT_Num`, `JO_Num`). Il n'y a **aucune ligne manquante, aucune colonne obligatoire vide**. La seule donnée optionnelle non renseignée est le couple responsable/caissier (`CO_No`/`CO_NoCaissier`, tous à 0).

## 3. Risque technique majeur identifié : les colonnes `cb*`

`F_CAISSE` contient des colonnes `cbCA_Intitule`, `cbCO_No`, `cbCO_NoCaissier`, `cbCT_Num` (et plus généralement `cbMarq`, `cbId`, `cbCreation*`...). Le préfixe `cb` et le type `varbinary` de `cbCA_Intitule` (qui contient réellement les octets ASCII de `CA_Intitule`, vérifié en le lisant) correspondent au mécanisme **"contrôle binaire"** de Sage 100 (famille Maestria) : une copie de contrôle que l'éditeur utilise pour détecter une modification faite **hors de son propre moteur** (anti-altération).

**Conséquence concrète** : un `INSERT` ou un `UPDATE` SQL direct sur `F_CAISSE` (même pour simplement renseigner `CO_NoCaissier`) ne mettrait à jour que la colonne visible, pas sa colonne `cb*` associée - donc **désynchronise volontairement les deux**, ce que Sage est justement censé détecter. Risque réel : la caisse pourrait apparaître comme altérée/suspecte dans le client Sage 100, voire être rejetée ou re-écrasée au prochain accès par Sage. Ce n'est pas qu'une question de "bonne pratique" (ne pas écrire dans la base d'un tiers) - c'est un risque d'intégrité technique démontré par la structure elle-même.

**Recommandation (déjà conforme à la règle absolue du projet depuis la Phase 1 initiale)** : ne rien écrire dans `F_CAISSE`, ni pour créer de nouvelles caisses (inutile, les 4 existent), ni pour compléter `CO_No`/`CO_NoCaissier` (risqué). Si un jour vous voulez renseigner le caissier d'une caisse côté Sage, il faut le faire **depuis le logiciel Sage 100 lui-même**, jamais par SQL direct - ce point sort du périmètre de ce projet.

## 4. Mapping réel app ↔ Sage aujourd'hui

| Caisse app (`SAGE_CAISSE_APP.CAISSES`) | `Numero_Caisse_Sage` | Caisse Sage réelle correspondante | Écart constaté |
|---|---|---|---|
| `CAISSE_SIEGE` ("Caisse Principale Siège") | 1 | "Caisse 1 Bijou SA" (`DE_No=1`→Bijou SA) | `Societe` app = `"SOCIETE_ABC"` (fictif) au lieu de `"Bijou SA"` ; `Responsable_Caisse=12` n'existe pas dans `F_COLLABORATEUR` (1 à 11 seulement) |
| `CAISSE_ATELIER` ("Caisse Menues Dépenses Atelier") | 2 | "Caisse 2 Bijou SA" (`DE_No=1`→Bijou SA) | Mêmes écarts (`SOCIETE_ABC`, `Responsable_Caisse=15` inexistant) |
| *(aucune)* | - | "Caisse 1 Annexe Bijou" (`CA_No=3`) | Caisse Sage réelle **non représentée** dans l'app |
| *(aucune)* | - | "Caisse 2 Annexe Bijou" (`CA_No=4`) | Caisse Sage réelle **non représentée** dans l'app |

`Compte_Financier` (app) n'a **aucune colonne correspondante dans `F_CAISSE`** - ce champ reste purement applicatif (saisi manuellement, déjà le cas aujourd'hui), la synchronisation ne le touchera jamais.

## 5. Plan proposé (sous réserve de votre validation - rien n'est encore développé)

Puisqu'il n'y a rien à créer dans BIJOU, je propose de **fusionner les Phases 2 et 3** du prompt en une seule étape de synchronisation **en lecture seule depuis BIJOU vers SAGE_CAISSE_APP** :

1. **Clé de correspondance** : `CAISSES.Numero_Caisse_Sage` (déjà existante) devient la clé d'appariement - jamais le nom, comme demandé. Ajout d'une contrainte `UNIQUE` dessus (NULL autorisé pour une caisse 100 % applicative, sans lien Sage) pour empêcher qu'une synchronisation répétée crée des doublons.
2. **Nouvelle fonction de lecture** (`objets_metier/lecture_sage.py: lister_caisses_sage`) : lit **toutes** les lignes de `F_CAISSE` (pas une seule par `CA_No` comme aujourd'hui), jointes à `F_DEPOT` pour résoudre la société réelle.
3. **Nouveau service de synchronisation** (`services/service_synchronisation_caisses.py`) avec une logique "upsert" idempotente :
   - Caisse Sage déjà connue (`Numero_Caisse_Sage` trouvé) → **met à jour uniquement les champs de référence** (`Nom_Caisse`, `Societe`) - ne touche **jamais** `Solde_Initial`, `Solde_Actuel`, `Statut`, ni aucune `OPERATIONS_CAISSE` déjà liée.
   - Caisse Sage inconnue → **crée** une nouvelle ligne `CAISSES` (les 2 caisses manquantes, `CA_No=3` et `4`).
   - Caisse app sans `Numero_Caisse_Sage` (si vous en créez une un jour sans lien Sage) → ignorée par la synchronisation, jamais supprimée.
4. **Traçabilité** : une colonne `Derniere_Synchro_Sage` (datetime, nullable) sur `CAISSES`, mise à jour à chaque passage ; le résultat de la synchronisation (nombre créées/mises à jour/ignorées, erreurs) est renvoyé au format `[SUCCES]/[ERREUR]` habituel et journalisé (réutilise `gestion_erreurs/journal.py`, Phase 8).
5. **Tests** : un test d'intégration avec une fausse liste de "caisses Sage" (évite de dépendre de la vraie base dans la suite automatisée, comme pour le reste du projet), + un test manuel réel contre `BIJOU`/`SAGE_CAISSE_APP` avant validation finale, en mode lecture-écriture temporaire comme d'habitude.
6. **Phase 4 (adaptation)** : endpoint `POST /caisses/synchroniser-depuis-sage` (MANAGER uniquement, soumis à `MODE_LECTURE_SEULE` comme toute écriture) + bouton correspondant dans `VueCaisses` (frontend), affichant le résultat (ex. "2 caisses créées, 2 mises à jour").

## 6. Ce qui ne change pas

- `ConnexionSageLectureSeule` reste strictement lecture seule - cette synchronisation n'ajoute **aucune** méthode d'écriture vers BIJOU.
- Les opérations de caisse (`OPERATIONS_CAISSE`) restent exclusivement gérées dans `SAGE_CAISSE_APP` (Phase 5 du prompt_4, explicitement hors périmètre).
- Aucune donnée existante de `SAGE_CAISSE_APP` n'est supprimée ou écrasée par la synchronisation.

## 7. Point de validation demandé

Le prompt demandait de préparer des requêtes SQL pour **créer ou compléter** des données dans BIJOU. L'analyse montre que ce n'est **pas nécessaire** (les 4 caisses existent et sont complètes) et serait même **risqué** pour les champs optionnels (`CO_NoCaissier`) à cause des colonnes `cb*`. Je propose donc de **ne rien écrire dans BIJOU** et de passer directement à la synchronisation en lecture (section 5) - étape 3/4 du plan initial, renommées Phase 2/3 fusionnées.

**Merci de valider avant que je commence à coder** : (a) ce renoncement à toute écriture dans BIJOU, (b) le plan de synchronisation ci-dessus (clé `Numero_Caisse_Sage`, upsert, `Derniere_Synchro_Sage`, endpoint MANAGER-only).
