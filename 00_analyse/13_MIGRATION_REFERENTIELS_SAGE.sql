-- Migration Phase 12 - referentiels Sage (tiers, collaborateurs), pour
-- remplacer les champs libres "code tiers"/"code collaborateur" du
-- formulaire d'operation par des combobox de noms reels.
-- A executer sur SAGE_CAISSE_APP uniquement (jamais sur BIJOU).
-- Additive uniquement : deux nouvelles tables, aucune donnee existante touchee.

CREATE TABLE TIERS_SAGE (
    CT_Num                  VARCHAR(17)   NOT NULL PRIMARY KEY,  -- = F_COMPTET.CT_Num (identifiant reel Sage)
    Intitule                 VARCHAR(69)   NOT NULL,
    Type_Tiers               SMALLINT      NULL,
    Derniere_Synchro_Sage    DATETIME      NOT NULL DEFAULT GETDATE()
);
GO

CREATE TABLE COLLABORATEURS_SAGE (
    CO_No                    INT           NOT NULL PRIMARY KEY,  -- = F_COLLABORATEUR.CO_No (identifiant reel Sage)
    Nom_Complet              VARCHAR(80)   NOT NULL,
    Caissier                 BIT           NOT NULL DEFAULT 0,
    Derniere_Synchro_Sage    DATETIME      NOT NULL DEFAULT GETDATE()
);
GO
