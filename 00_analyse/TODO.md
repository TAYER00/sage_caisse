# À faire / pistes différées — sage_caisse

## 1. (Différé, non prioritaire) Utiliser les objets métier CPTA.Base.18 pour les lectures Sage

Constat (voir `03_OBJETS_METIER_SAGE100.md`) : `CPTA.Base.18` expose réellement et avec succès des objets pour :
- `CompteTs` / `ReadCompteTNumero` (tiers)
- `CompteGs` / `ReadCompteGNumero` (comptes généraux)
- `Journauxs` / `ReadJournauxNumero` (journaux)
- `EcritureCs` / `QueryEcritureCCompteGOrderDate` (écritures comptables)

Actuellement, `sage_caisse` lit tout en SQL direct (`ConnexionSageLectureSeule`), ce qui fonctionne et respecte le prompt. Si on veut un jour s'aligner avec le pattern objets métier de `sage_Conex_CRUD` (plutôt que SQL direct) pour ces 4 tables, c'est possible et déjà vérifié avec de vraies données. **Non fait pour l'instant** - pas nécessaire, SQL suffit.

Rappel : **aucune** piste d'objet métier n'existe pour `F_CAISSE` ni `F_CREGLEMENT` (vérifié, absent de l'interface réelle ET de la documentation installée) - ces deux tables resteront toujours en SQL direct, quoi qu'il arrive.
