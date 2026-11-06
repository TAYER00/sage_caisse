# Conversion des requêtes SQL en objets métier Sage 100

> Toutes les affirmations ci-dessous sont **vérifiées par un test réel** sur ce poste (tentatives d'instanciation COM, lectures réelles), pas déduites de la documentation seule. Aucune écriture n'a été effectuée - uniquement des méthodes `Read*`/`Query*` (lecture) et `Open()`/`Close()`.

## 1. Résultat principal : la documentation PDF ne correspond pas à ce qui est installé ici

`docs\V12_Sage 100cloud Objets metiers v1220.pdf` documente une famille d'objets **"IBO\*"** (ex. `IBODocumentReglement` pour les règlements en Gestion commerciale, `IBOTiersReglement3` pour les règlements tiers en Comptabilité), accessible via deux classes COM : `BSCPTAApplication100c` (comptabilité) et `BSCIALApplication100c` (commerciale).

**Test réel effectué** (instanciation COM, sans ouvrir aucune base) :

```python
import win32com.client
for progid in ['BSCPTAApplication100c', 'BSCIALApplication100c', 'IBOTiersReglement3', 'IBODocumentReglement']:
    win32com.client.gencache.EnsureDispatch(progid)
```

**Résultat : les 4 échouent**, avec l'erreur COM `-2147221005 "Chaîne de classe incorrecte"` (= la classe n'est pas enregistrée sur ce poste). Donc :

> Aucun des objets métier décrits dans ce PDF pour les règlements (`IBODocumentReglement`, `IBOTiersReglement3`) n'est utilisable ici. Ce n'est pas un problème de code - c'est que ce composant Sage n'est pas installé sur cette machine (déjà constaté pour la Gestion Commerciale dans `sage_Conex_CRUD/00_analyse/04_VERIFICATION_COM.md`).

## 2. Ce qui fonctionne réellement sur ce poste

Un **autre** moteur d'objets métier, plus ancien (famille "Maestria"), est bien installé et fonctionnel : `CPTA.Base.18` - c'est celui déjà utilisé et vérifié dans `sage_Conex_CRUD` pour lire les tiers.

**Test réel** : instanciation réussie, puis inspection de tous les membres exposés :

```python
import win32com.client
base = win32com.client.gencache.EnsureDispatch('CPTA.Base.18')
print([m for m in dir(base) if not m.startswith('_')])
```

Résultat réel (extrait pertinent) :

```
CompteA, CompteG, CompteGs, CompteTs, EcritureC, EcritureCs, Journaux, Journauxs,
ReadCompteANumero, ReadCompteGNumero, ReadCompteTNumero, ReadEcritureCNumero, ReadJournauxNumero,
QueryCompteGTypeOrderNumero, QueryCompteTTypeOrderNumero,
QueryEcritureCCompteGOrderDate, QueryEcritureCPeriodeOrderJour, QueryJournauxTypeOrderNumero, ...
```

**Constat clé** : il n'existe **aucun membre `Caisse`, `Caisses`, `CReglement` ou `Reglement`** (au sens d'une collection d'enregistrements) dans cette interface. Seuls les comptes généraux (`CompteGs`), les tiers (`CompteTs`), les journaux (`Journauxs`) et **les écritures comptables (`EcritureCs`)** sont exposés.

## 3. Vérification avec de vraies données (base BIJOU, lecture seule)

```python
base.Open(r'C:\Users\Public\Documents\Sage\Entreprise 100c\BIJOU.MAE')

base.ReadCompteGNumero('5310')        # -> CG_Num=5310, CG_Intitule="Caisse en euro"
base.ReadJournauxNumero('CAIS')       # -> JO_Num=CAIS, JO_Intitule="Caisse"
base.ReadEcritureCNumero(315)         # -> EC_No=315, "Achat de timbres", 100.0

liste = base.QueryEcritureCCompteGOrderDate('5310', date_debut, date_fin)
# -> 7 écritures réelles trouvées sur le compte "Caisse en euro", dont les 6 déjà
#    identifiées en SQL sur le journal CAIS (chaque élément expose .JO_Num,
#    ce qui permet de filtrer "comme un WHERE JO_Num = 'CAIS'" côté Python)

base.Close()
```

**Résultat réel, exactement identique à ce qu'on avait trouvé en SQL** - confirme que l'objet métier `EcritureCs` est une alternative fiable à la lecture SQL directe pour cette table.

## 4. Tableau de conversion — SQL (section 5.1) → Objet métier

| Requête SQL (besoin)                              | Table Sage          | Objet métier disponible ?                                                               | Comment faire en objets métier                                                                                                                                |
| -------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Écritures de caisse (journal `CAIS`)            | `F_ECRITUREC`     | ✅ **Oui, vérifié**                                                              | `base.QueryEcritureCCompteGOrderDate(CG_Num, debut, fin)` puis filtrer en Python sur `.JO_Num == 'CAIS'` (pas de méthode de requête directe par journal) |
| Lire une écriture précise                        | `F_ECRITUREC`     | ✅ **Oui, vérifié**                                                              | `base.ReadEcritureCNumero(EC_No)`                                                                                                                            |
| Lister les caisses                                 | `F_CAISSE`        | ❌ **Aucun objet, ni documenté ni réel**                                         | **SQL obligatoire** (`ConnexionSageLectureSeule.executer_lecture`)                                                                                     |
| Lister les caissiers/responsables                  | `F_COLLABORATEUR` | ❌ **Aucun objet, ni documenté ni réel**                                         | **SQL obligatoire**                                                                                                                                      |
| Comptes financiers (classe 5)                      | `F_COMPTEG`       | ✅ **Oui, vérifié**                                                              | `base.QueryCompteGTypeOrderNumero(...)` / `base.ReadCompteGNumero(CG_Num)`                                                                                 |
| Journaux                                           | `F_JOURNAUX`      | ✅ **Oui, vérifié**                                                              | `base.QueryJournauxTypeOrderNumero(...)` / `base.ReadJournauxNumero(JO_Num)`                                                                               |
| Tiers (bénéficiaires)                            | `F_COMPTET`       | ✅ **Oui, déjà vérifié dans `sage_Conex_CRUD`**                              | `base.QueryCompteTTypeOrderNumero(...)` / `base.ReadCompteTNumero(CT_Num)`                                                                                 |
| **Règlements** (`F_CREGLEMENT` lui-même) | `F_CREGLEMENT`    | ❌ **Aucun objet, ni documenté (non installé) ni réel (absent de l'interface)** | **SQL obligatoire, sans alternative**                                                                                                                    |

## 5. Conclusion — ce que cela change pour le projet

**Rien ne change dans l'approche déjà choisie en Phase 1**, mais on sait maintenant précisément *pourquoi* c'est la bonne approche, et pas un raccourci :

- Pour **`F_CREGLEMENT`** (la table centrale du projet) et **`F_CAISSE`** : **aucun objet métier n'existe sur ce poste**, documenté ou réel. La lecture SQL directe (`ConnexionSageLectureSeule`, déjà écrite et testée en Phase 1) reste la **seule** solution - ce n'est pas qu'on évite les objets métier par facilité, c'est qu'ils n'existent pas ici pour ces deux tables.
- Pour **`F_COMPTET`, `F_COMPTEG`, `F_JOURNAUX`, `F_ECRITUREC`** : un objet métier réel existe (`CPTA.Base.18`). Ce n'est **pas nécessaire** pour ce projet (le prompt demande explicitement de rester en lecture seule, et SQL fait très bien le travail), mais c'est une option disponible si un jour vous préférez cette voie pour la cohérence avec `sage_Conex_CRUD`.
- **Aucune conséquence sur le mode autonome recommandé** (section "Distinction importante" du prompt) : notre application continue d'écrire uniquement dans sa propre base, jamais dans Sage - ce constat concerne uniquement la **lecture**.

## 6. Prochaine étape

Ce document répond à votre demande de conversion SQL → objets métier. Il n'ajoute aucune nouvelle tâche de développement : l'approche SQL de la Phase 1 est confirmée comme la seule viable pour `F_CREGLEMENT`/`F_CAISSE`.

**Je reste en attente de votre validation sur la Phase 2** (champs retenus dans `02_DICTIONNAIRE_FONCTIONNEL_CAISSE.md`, champ `Projet`, règles de gestion proposées) avant de passer à la Phase 3.
