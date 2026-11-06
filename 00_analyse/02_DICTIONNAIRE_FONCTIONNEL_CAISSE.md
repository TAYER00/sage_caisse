# PHASE 2 — Dictionnaire fonctionnel et analyse de F_CREGLEMENT pour le besoin "caisse"

> Lecture seule, toutes les données citées sont vérifiées par requête réelle sur `BIJOU`. Aucune table Sage modifiée. **Vous décidez seul des champs à exploiter** - ce document présente les candidats, pas une décision prise à votre place.

## 0. Constat majeur — répond à la question "F_CREGLEMENT est-elle suffisante ?"

**Non, pas seule.** Voici ce qui a été vérifié réellement :

| Table | Lignes réelles | Constat |
|---|---|---|
| `F_CREGLEMENT` | **0** | Vide - aucun règlement n'a jamais été saisi dans cette base de démo |
| `F_ECRITUREC` | **561** | Contient de vraies écritures comptables |
| → dont journal `CAIS` (Caisse) | **12** | **Des opérations de caisse réelles existent, mais ont été saisies directement en écriture comptable, pas via F_CREGLEMENT** |

Exemples réels trouvés dans `F_ECRITUREC` (journal `CAIS`) :

| EC_No | Date | Compte général | Montant | Intitulé |
|---|---|---|---|---|
| 315/316 | 2026-01-09 | `626000` (Frais postaux et télécommunications) / `5310` (Caisse en euro) | 100 | Achat de timbres |
| 313/314 | 2026-01-09 | `626000` / `5310` | 360 | Achat de 3 cartes téléphoniques |
| 312 | 2026-01-09 | `5310` | 1000 | Virement interne |

**Conséquence concrète pour le projet** : si vous voulez un jour retrouver l'historique réel des dépenses de caisse déjà saisies dans Sage (avant notre application), il faudra regarder `F_ECRITUREC` filtrée sur `JO_Num = 'CAIS'` (et les autres journaux `JO_Reglement = 1`, voir section 3), pas seulement `F_CREGLEMENT`. Pour les **nouvelles** opérations créées par notre application (mode autonome, recommandé par le prompt), ce point n'a pas d'impact immédiat : elles vivront dans notre propre base, pas dans Sage.

## 1. Dictionnaire fonctionnel de F_CREGLEMENT

Format exact demandé : **Champ Sage | Type SQL | Signification technique | Traduction française simple | Utilité dans l'application**.

Seuls les champs métier sont listés (les 22 champs techniques `cb*` n'ont aucune utilité applicative - détaillés si besoin dans `docs/analyse_detaillee_f_creglement.md`).

### 1.1 Champs déjà présélectionnés par vous (section "NOTES FONCTIONNELLES" du prompt)

| Champ Sage | Type SQL | Signification technique | Traduction française simple | Utilité dans l'application |
|---|---|---|---|---|
| `RG_No` | `int` | Compteur auto-incrémenté, clé métier unique | Numéro du règlement | Référence à afficher (lecture seule), et clé pour lier notre future table `CORRESPONDANCE_REGLEMENTS` |
| `RG_Date` | `datetime` | Date de l'opération | Date de l'opération | Champ de saisie obligatoire, tri par défaut de la liste |
| `RG_TypeReg` | `smallint`, code 0 à 8 | Nature précise de l'opération (0=Règlement, 1=Acompte, 2=Fond de caisse, 3=Remise en banque, 4=Sortie de caisse, 5=Entrée en caisse, 6=Remise à 0, 7=Contrôle de caisse, 8=Bon d'achat) | Type d'opération | **Candidat direct** pour mapper vers notre "Type d'opération" (Alimentation/Dépense/Remboursement) - voir section 4, attention : le mapping n'est pas 1-pour-1 |
| `RG_Libelle` | `varchar(35)` | Libellé texte libre | Motif / Description | Champ de saisie "Motif" |
| `RG_Montant` | `numeric(24,6)` | Montant en devise société | Montant | Champ de saisie obligatoire, doit être > 0 |
| `RG_Reference` | `varchar(17)` (type réel - la doc Sage indique 8 caractères, écart déjà signalé) | Référence libre | Référence / n° de justificatif | Peut servir à stocker une référence de pièce, pas le fichier lui-même |
| `CA_No` | `int` | Identifiant de la caisse | Caisse | Combobox "Caisse" - alimentée en lisant `F_CAISSE` |
| `CT_NumPayeur` | `varchar(17)` | Code du tiers payeur/bénéficiaire | Bénéficiaire / Tiers | Combobox "Bénéficiaire" - alimentée en lisant `F_COMPTET` |
| `CO_NoCaissier` | `int` | Identifiant du collaborateur caissier | Responsable / Caissier | Combobox "Responsable" - idéalement filtrée sur `F_COLLABORATEUR.CO_Caissier = 1` (voir section 3, 3 collaborateurs réels sont flagués caissiers) |
| `N_Reglement` | `smallint`, code 1 à 30 | Mode de règlement (table de paramétrage non analysée) | Mode de règlement | Combobox, **hors périmètre de cette phase** - à analyser séparément (table de paramétrage Sage non vérifiée) |
| `CG_Num` | `varchar(13)` | Compte comptable principal | Compte général | Combobox "Compte financier" - alimentée en lisant `F_COMPTEG` (313 comptes réels, ex. `5310` = "Caisse en euro") |
| `JO_Num` | `varchar(7)` **obligatoire** | Code journal comptable | Journal comptable | Combobox - alimentée en lisant `F_JOURNAUX` (18 journaux réels, dont `CAIS` = "Caisse") |
| `RG_Valide` | `smallint` (0/1) | Statut de validation Sage | Statut de validation | **Attention** (rappel du prompt) : ceci est le statut **de Sage**, pas forcément celui de notre workflow applicatif (Brouillon/Validé/Comptabilisé/Annulé) - à ne pas confondre |
| `RG_Compta` | `smallint` (0/1) | Le règlement est-il comptabilisé dans Sage | Comptabilisé | Idem : statut Sage, distinct de notre statut "Comptabilisé" interne |

### 1.2 Champs complémentaires que vous avez indiqués (section avancée)

| Champ Sage | Type SQL | Signification technique | Traduction française simple | Utilité dans l'application |
|---|---|---|---|---|
| `RG_Cloture` | `smallint` **NOT NULL** | Règlement clôturé | Caisse clôturée | Section avancée - verrouillage après clôture |
| `RG_Impaye` | `datetime` | Date de passage en impayé | Date d'impayé | Section avancée - suivi des impayés, probablement non pertinent pour de simples dépenses de caisse |
| `RG_Banque` | `smallint` (0/1) | Remis en banque ou non | Remise en banque | Section avancée |
| `RG_Transfere` | `smallint` (0/1) | Règlement transféré | Transfert effectué | Section avancée |

### 1.3 Autres champs métier existants, non présélectionnés (à votre décision)

| Champ Sage | Type SQL | Signification technique | Traduction française simple | Utilité potentielle |
|---|---|---|---|---|
| `RG_MontantDev` | `numeric(24,6)` | Montant en devise étrangère | Montant en devise | Utile seulement si multi-devises envisagé - le prompt mentionne "Devise" comme champ fonctionnel, donc probablement pertinent |
| `N_Devise` | `smallint` | Code devise | Devise | Idem - combobox "Devise" du formulaire |
| `RG_Cours` | `numeric(24,6)` | Cours de change | Cours devise | Utile seulement si multi-devises |
| `RG_Type` | `smallint` (0/1/2) | Client/Fournisseur/Autre | Type de tiers | Pourrait servir à filtrer la liste "Bénéficiaire" selon le contexte |
| `RG_Impute` | `smallint` (0/1) | Déjà affecté à une échéance | Imputé | Peu pertinent pour une simple dépense de caisse sans échéance |
| `EC_No` | `int` | Écriture comptable liée | Référence comptable Sage | **Important pour plus tard** : c'est exactement le champ "Référence comptable Sage si disponible" demandé dans le statut "Comptabilisé" du prompt |
| `CG_NumCont` | `varchar(13)` | Compte de contrepartie | Compte de contrepartie | Pertinent si on veut prévoir la contrepartie comptable à l'avance |
| `CT_NumPayeurOrig` | `varchar(17)` | Payeur d'origine | Bénéficiaire d'origine | Peu pertinent sauf si on gère des réaffectations |
| `RG_DateEchCont` | `datetime` | Échéance de contrepartie | — | Peu pertinent pour une dépense de caisse simple |
| `CG_NumEcart` / `JO_NumEcart` / `RG_MontantEcart` | — | Gestion des écarts (ex. change) | Écart | Peu pertinent sauf multi-devises |
| `RG_NoBonAchat` | `int` | Lien vers un bon d'achat | — | Hors périmètre (spécifique au commerce, pas à la caisse de dépenses) |
| `RG_Anterieur` | `numeric(24,6)` | Montant déjà imputé avant | — | Peu pertinent pour une dépense simple |
| `RG_MontantCommission` / `RG_MontantNet` | `numeric(24,6)` | Paiement en ligne (commission/net) | — | Hors périmètre sauf si paiement en ligne envisagé |
| `RG_Heure` | `char(9)` | Heure | Heure | Déjà noté "usage interne, ne pas renseigner en saisie" selon Sage |
| `RG_Piece` | `varchar(13)` | Numéro de pièce | — | Peut doubler avec `RG_Reference`, à clarifier avec vous |
| `RG_Souche` / `RG_Ticket` | `smallint` | Spécifique aux tickets de caisse commerciale | — | Hors périmètre (ce projet gère des dépenses, pas des ventes au comptoir) |

### 1.4 Champ complémentaire demandé — `Projet` (NOUVEAU, n'existe pas dans Sage)

| Champ | Type SQL proposé | Signification | Traduction française simple | Utilité dans l'application |
|---|---|---|---|---|
| `Projet` | `VARCHAR(100)` **optionnel** (`NULL` autorisé) | Libellé libre identifiant le projet/déplacement/contexte de la dépense | Projet | Permet de regrouper et filtrer les opérations par projet (ex. "Déplacement Lyon"), **indépendamment** de la caisse ou du responsable. Champ texte simple au départ - pourra devenir une combobox dynamique plus tard si une vraie liste de projets émerge (même logique que "Motif de dépense" dans le prompt). |

**Important** : `Projet` n'existe dans aucune table Sage (`F_CREGLEMENT` comme les autres tables examinées). C'est un champ **propre à notre base applicative** `sage_caisse` (table `OPERATIONS_CAISSE`, à créer en Phase 3) - exactement comme `CORRESPONDANCE_ARTICLES` dans `sage_to_shopify` contenait des colonnes qui n'existaient pas côté Sage. Il sera ajouté au schéma proposé en Phase 3.

## 2. Autres tables Sage examinées (réellement, pas supposées)

| Table | Lignes réelles | Champs métier clés (hors `cb*`) | Utilité confirmée |
|---|---|---|---|
| `F_CAISSE` | **4** | `CA_No`, `CA_Intitule`, `DE_No`, `CO_No`, `CO_NoCaissier`, `CT_Num`, `JO_Num` | Alimente directement la combobox "Caisse". Exemple réel : `CA_No=1`, "Caisse 1 Bijou SA" |
| `F_COMPTET` | **68** | `CT_Num`, `CT_Intitule`, `CT_Type` (0=Client,1=Fournisseur,2=Salarié,3=Autre - confirmé sur sage_Conex_CRUD), `CG_NumPrinc` | Alimente "Bénéficiaire". Exemple réel : `BILLO` (Billot), `CT_Type=1`, `CG_NumPrinc=4010000` |
| `F_COLLABORATEUR` | **11** | `CO_No`, `CO_Nom`, `CO_Prenom`, `CO_Caissier` (0/1), `CO_Service` | Alimente "Responsable/Caissier". **3 collaborateurs réels sont flagués caissiers** : ECLAT Dorine, HAMAND Eddy, PANDAN Tiffany |
| `F_COMPTEG` | **313** | `CG_Num`, `CG_Intitule` | Alimente "Compte financier". Exemple réel : `5310` = "Caisse en euro" |
| `F_JOURNAUX` | **18** | `JO_Num`, `JO_Intitule`, `JO_Reglement` (0/1) | Alimente "Journal comptable". **11 journaux sur 18 sont marqués `JO_Reglement=1`** (dont `CAIS` = "Caisse", `BEU`/`BRD` = banques) |
| `F_ECRITUREC` | **561** | `EC_No`, `EC_Date`, `CG_Num`, `CT_Num`, `EC_Sens`, `EC_Montant` | **12 écritures réelles sur le journal `CAIS`** - voir constat majeur section 0 |
| `F_REGLECH` | **0** | — | Vide, comme `F_CREGLEMENT` - pas de données exploitables actuellement |
| `F_CAISSETOTAL` | **0** | — | Vide - pas de données de totalisation de caisse actuellement |

## 3. Relations (confirmées vs documentées - même méthode que `docs/analyse_detaillee_f_creglement.md`)

| Relation | Type |
|---|---|
| `F_CREGLEMENT.cbCA_No → F_CAISSE.CA_No` | ✅ Contrainte FK réelle en base |
| `F_REGLECH.RG_No → F_CREGLEMENT.RG_No` | ✅ Contrainte FK réelle en base |
| `F_CREGLEMENT.CT_NumPayeur → F_COMPTET.CT_Num` | Documentée Sage, non contrainte physiquement |
| `F_CREGLEMENT.CO_NoCaissier → F_COLLABORATEUR.CO_No` | Documentée Sage, non contrainte physiquement |
| `F_CREGLEMENT.CG_Num → F_COMPTEG.CG_Num` | Documentée Sage, non contrainte physiquement |
| `F_CREGLEMENT.JO_Num → F_JOURNAUX.JO_Num` | Documentée Sage, non contrainte physiquement |
| `F_CREGLEMENT.EC_No → F_ECRITUREC.EC_No` | Documentée Sage, non contrainte physiquement |
| `F_ECRITUREC.JO_Num → F_JOURNAUX.JO_Num` | Documentée Sage (vérifiée par les données réelles : toutes les `JO_Num='CAIS'` existent bien dans `F_JOURNAUX`) |

## 4. Règles de gestion possibles (propositions, pas des décisions)

À valider avec vous avant toute implémentation (Phase 3+) :

1. **Mapping `RG_TypeReg` → notre "Type d'opération"** (proposition, à discuter) :
   - `RG_TypeReg=4` (Sortie de caisse) → Dépense
   - `RG_TypeReg=5` (Entrée en caisse) → Alimentation
   - `RG_TypeReg=1` (Acompte) → possiblement un remboursement ou une avance, **sens à clarifier avec vous** (le prompt interdit explicitement de supposer le sens financier d'un remboursement)
   - Les autres valeurs (0,2,3,6,7,8) semblent hors périmètre "dépenses d'employés" (plutôt liés à la caisse commerciale/vente)
2. **Calcul du solde d'une caisse** : somme des opérations validées rattachées à `CA_No`, alimentation = `+montant`, dépense = `-montant`, remboursement = **à définir avec vous selon le cas réel** (ex. remboursement d'une avance employé = `-montant` du point de vue de l'employé mais `+montant` du point de vue de la caisse).
3. **Journal comptable par défaut** : `CAIS` (JO_Reglement=1) semble être le journal naturel pour les opérations de caisse de ce projet, confirmé par les 12 écritures réelles déjà trouvées dessus.
4. **Caissiers éligibles** : filtrer `F_COLLABORATEUR` sur `CO_Caissier = 1` pour peupler la combobox "Responsable/Caissier" plutôt que d'afficher les 11 collaborateurs sans filtre.

## 5. Requêtes SQL utiles pour retrouver l'information facilement

Deux familles de requêtes, bien distinctes :

- **5.1** : requêtes **Sage réelles**, utilisables **dès maintenant** en lecture seule (le compte `BIJOU_READONLY` suffit).
- **5.2** : requêtes **anticipées** sur la future table applicative `OPERATIONS_CAISSE` (base `sage_caisse`, pas encore créée - schéma proposé en Phase 3, inclut déjà le champ `Projet` de la section 1.4). Elles ne sont **pas exécutables aujourd'hui** : elles servent de référence pour vérifier, dès la conception du schéma, que ces recherches seront bien possibles.

### 5.1 Dès maintenant — sur Sage (lecture seule)

```sql
-- Les 12 opérations de caisse réelles déjà trouvées (journal CAIS)
SELECT EC_No, EC_Date, CT_Num, CG_Num, EC_Sens, EC_Montant, EC_Intitule
FROM F_ECRITUREC
WHERE JO_Num = 'CAIS'
ORDER BY EC_Date DESC;

-- Lister les caisses disponibles (pour peupler la combobox "Caisse")
SELECT CA_No, CA_Intitule, DE_No, CO_NoCaissier
FROM F_CAISSE
ORDER BY CA_Intitule;

-- Lister uniquement les collaborateurs réellement caissiers (pour la combobox "Responsable")
SELECT CO_No, CO_Nom, CO_Prenom, CO_Service
FROM F_COLLABORATEUR
WHERE CO_Caissier = 1
ORDER BY CO_Nom;

-- Lister les comptes de caisse/trésorerie (classe 5) pour la combobox "Compte financier"
SELECT CG_Num, CG_Intitule
FROM F_COMPTEG
WHERE CG_Num LIKE '5%'
ORDER BY CG_Num;

-- Lister les tiers (pour la combobox "Bénéficiaire")
SELECT CT_Num, CT_Intitule, CT_Type
FROM F_COMPTET
ORDER BY CT_Intitule;
```

### 5.2 À anticiper — sur la future table `OPERATIONS_CAISSE` (Phase 3, pas encore créée)

Schéma anticipé minimal (d'après le dictionnaire ci-dessus + le champ `Projet`) : `Reference`, `Type_Operation`, `Numero_Caisse`, `Date_Operation`, `Motif`, `Beneficiaire`, `Responsable`, `Societe`, `Compte_Financier`, `Compte_Analytique`, `Montant`, `Devise`, `Projet`, `Observation`, `Statut`.

```sql
-- Lister toutes les dépenses, les plus récentes en premier
SELECT Reference, Date_Operation, Numero_Caisse, Beneficiaire, Responsable, Projet, Montant, Statut
FROM OPERATIONS_CAISSE
WHERE Type_Operation = 'DEPENSE'
ORDER BY Date_Operation DESC;

-- Rechercher par caisse
SELECT * FROM OPERATIONS_CAISSE
WHERE Numero_Caisse = ?
ORDER BY Date_Operation DESC;

-- Rechercher par projet
SELECT * FROM OPERATIONS_CAISSE
WHERE Projet = ?
ORDER BY Date_Operation DESC;

-- Rechercher par responsable
SELECT * FROM OPERATIONS_CAISSE
WHERE Responsable = ?
ORDER BY Date_Operation DESC;

-- Recherche combinée (caisse + projet + responsable + période) - les filtres non fournis sont ignorés
SELECT * FROM OPERATIONS_CAISSE
WHERE (Numero_Caisse = ? OR ? IS NULL)
  AND (Projet = ? OR ? IS NULL)
  AND (Responsable = ? OR ? IS NULL)
  AND Date_Operation BETWEEN ? AND ?
ORDER BY Date_Operation DESC;

-- Recherche texte libre (motif, observation ou projet) - équivalent de la "recherche rapide" du prompt
SELECT * FROM OPERATIONS_CAISSE
WHERE Motif LIKE '%' + ? + '%'
   OR Observation LIKE '%' + ? + '%'
   OR Projet LIKE '%' + ? + '%'
ORDER BY Date_Operation DESC;

-- Total des dépenses par caisse (pour un tableau de synthèse)
SELECT Numero_Caisse, SUM(Montant) AS Total_Depenses
FROM OPERATIONS_CAISSE
WHERE Type_Operation = 'DEPENSE' AND Statut IN ('VALIDE', 'COMPTABILISE')
GROUP BY Numero_Caisse;

-- Total des dépenses par projet
SELECT Projet, SUM(Montant) AS Total_Depenses
FROM OPERATIONS_CAISSE
WHERE Type_Operation = 'DEPENSE' AND Projet IS NOT NULL
GROUP BY Projet
ORDER BY Total_Depenses DESC;

-- Total des dépenses par responsable
SELECT Responsable, SUM(Montant) AS Total_Depenses
FROM OPERATIONS_CAISSE
WHERE Type_Operation = 'DEPENSE'
GROUP BY Responsable
ORDER BY Total_Depenses DESC;
```

> Ces requêtes anticipées seront reprises telles quelles (ou ajustées selon vos retours) comme base des fonctions `lister()`/`rechercher()` du module `objets_metier` en Phase 4, et des filtres de l'interface liste en Phase 6.

## 6. Prochaine étape

**En attente de votre validation explicite** (rappel du prompt, Phase 2) sur :
- Les champs de la section 1.1/1.2 à conserver tels quels (priorité haute).
- Les champs de la section 1.3 à inclure ou exclure.
- Les 4 règles de gestion proposées en section 4 (notamment le sens du "remboursement").

Je n'avancerai pas sur la Phase 3 (conception du schéma applicatif) sans cette validation.
