-- ============================================================================
-- SCRIPT PROPOSE - NON EXECUTE - EN ATTENTE DE VOTRE ACCORD (Phase 3)
-- Base cible : SAGE_CAISSE_APP (nom a valider)
-- Ne touche JAMAIS a Sage (BIJOU) ni a aucune autre base existante.
-- ============================================================================

-- Etape 0 : creation de la base dediee (si vous validez le nom)
-- IF DB_ID('SAGE_CAISSE_APP') IS NULL CREATE DATABASE SAGE_CAISSE_APP;
-- GO
-- USE SAGE_CAISSE_APP;
-- GO
-- SELECT DB_NAME() AS base_courante;  -- doit afficher SAGE_CAISSE_APP avant de continuer
-- GO

-- ----------------------------------------------------------------------------
-- 1. UTILISATEURS
-- Ajoutee par rapport a la liste du prompt : necessaire pour la tracabilite
-- (createur/validateur/comptable) demandee dans "SECURITE ET TRACABILITE".
-- ----------------------------------------------------------------------------
CREATE TABLE UTILISATEURS (
    Id_Utilisateur      INT IDENTITY(1,1) PRIMARY KEY,
    Login               VARCHAR(50)   NOT NULL,
    Mot_De_Passe_Hash   VARCHAR(255)  NOT NULL,   -- jamais en clair
    Nom_Complet         VARCHAR(100)  NOT NULL,
    Role                VARCHAR(10)   NOT NULL DEFAULT 'USER',
    Actif               BIT           NOT NULL DEFAULT 1,
    Date_Creation       DATETIME      NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_Utilisateurs_Login UNIQUE (Login),
    CONSTRAINT CK_Utilisateurs_Role CHECK (Role IN ('USER', 'MANAGER'))
);
GO

-- ----------------------------------------------------------------------------
-- 2. PARAMETRES_CAISSE
-- Listes dynamiques (motifs, etc.) - jamais de suppression physique si utilisee,
-- seulement Actif = 0 (regle explicite du prompt).
-- ----------------------------------------------------------------------------
CREATE TABLE PARAMETRES_CAISSE (
    Id_Parametre    INT IDENTITY(1,1) PRIMARY KEY,
    Categorie       VARCHAR(30)   NOT NULL,   -- ex: 'MOTIF'
    Code            VARCHAR(30)   NOT NULL,
    Libelle         VARCHAR(100)  NOT NULL,
    Actif           BIT           NOT NULL DEFAULT 1,
    Date_Creation   DATETIME      NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_ParametresCaisse_CategorieCode UNIQUE (Categorie, Code)
);
GO

-- ----------------------------------------------------------------------------
-- 3. CAISSES
-- Reference optionnelle a F_CAISSE.CA_No (Sage) - PAS de contrainte FK physique
-- (base differente) : validee au niveau applicatif.
-- ----------------------------------------------------------------------------
CREATE TABLE CAISSES (
    Id_Caisse               INT IDENTITY(1,1) PRIMARY KEY,
    Code_Caisse             VARCHAR(20)   NOT NULL,
    Nom_Caisse               VARCHAR(100)  NOT NULL,
    Societe                  VARCHAR(50)   NOT NULL,
    Numero_Caisse_Sage       INT           NULL,       -- = F_CAISSE.CA_No (mapping optionnel)
    Compte_Financier         VARCHAR(13)   NULL,       -- = F_COMPTEG.CG_Num (documente, non contraint)
    Responsable_Caisse       INT           NULL,       -- = F_COLLABORATEUR.CO_No (documente, non contraint)
    Devise                   VARCHAR(3)    NOT NULL DEFAULT 'EUR',
    Solde_Initial            NUMERIC(18,2) NOT NULL DEFAULT 0,
    Solde_Actuel             NUMERIC(18,2) NOT NULL DEFAULT 0,  -- CACHE recalcule par l'application, jamais modifie directement
    Statut                   VARCHAR(10)   NOT NULL DEFAULT 'ACTIF',
    Date_Creation            DATETIME      NOT NULL DEFAULT GETDATE(),
    Derniere_Synchro_Sage    DATETIME      NULL,       -- Phase 11 : derniere synchro depuis BIJOU.F_CAISSE
    CONSTRAINT UQ_Caisses_Code UNIQUE (Code_Caisse),
    CONSTRAINT UQ_Caisses_NumeroCaisseSage UNIQUE (Numero_Caisse_Sage),  -- Phase 11 : cle d'appariement sync (NULL autorises multiples)
    CONSTRAINT CK_Caisses_Statut CHECK (Statut IN ('ACTIF', 'INACTIF'))
);
GO

-- ----------------------------------------------------------------------------
-- 4. OPERATIONS_CAISSE
-- Table centrale. Comprend le champ "Projet" (demande) et "Sens_Solde" (resout
-- le point ouvert "sens financier d'un remboursement" - voir 04_PHASE3_...md).
-- ----------------------------------------------------------------------------
CREATE TABLE OPERATIONS_CAISSE (
    Id_Operation              INT IDENTITY(1,1) PRIMARY KEY,
    Reference                 VARCHAR(20)    NOT NULL,          -- numero automatique, genere par l'application
    Type_Operation             VARCHAR(15)    NOT NULL,          -- ALIMENTATION / DEPENSE / REMBOURSEMENT
    Sens_Solde                 VARCHAR(7)     NOT NULL,          -- ENTREE / SORTIE - voir section 2 du document Phase 3
    Id_Caisse                  INT            NOT NULL,
    Date_Operation              DATETIME       NOT NULL,
    Id_Motif                   INT            NULL,              -- = PARAMETRES_CAISSE.Id_Parametre (Categorie='MOTIF')
    Beneficiaire                VARCHAR(17)    NULL,              -- = F_COMPTET.CT_Num (documente, non contraint)
    Responsable                 INT            NULL,              -- = F_COLLABORATEUR.CO_No (documente, non contraint)
    Societe                     VARCHAR(50)    NULL,
    Compte_Financier             VARCHAR(13)    NULL,              -- = F_COMPTEG.CG_Num (documente, non contraint)
    Compte_Analytique            VARCHAR(20)    NULL,
    Montant                      NUMERIC(18,2)  NOT NULL,
    Devise                       VARCHAR(3)     NOT NULL DEFAULT 'EUR',
    Projet                       VARCHAR(100)   NULL,              -- champ ajoute a votre demande
    Observation                  VARCHAR(500)   NULL,
    Statut                       VARCHAR(15)    NOT NULL DEFAULT 'BROUILLON',
    Cree_Par                     INT            NOT NULL,
    Date_Creation                DATETIME       NOT NULL DEFAULT GETDATE(),
    Modifie_Par                  INT            NULL,
    Date_Modification            DATETIME       NULL,
    Valide_Par                   INT            NULL,
    Date_Validation               DATETIME       NULL,
    Comptabilise_Par             INT            NULL,
    Date_Comptabilisation         DATETIME       NULL,
    Reference_Comptable_Sage      INT            NULL,              -- = F_ECRITUREC.EC_No, rempli UNIQUEMENT si mode integre active plus tard
    CONSTRAINT UQ_OperationsCaisse_Reference UNIQUE (Reference),
    CONSTRAINT FK_OperationsCaisse_Caisse FOREIGN KEY (Id_Caisse) REFERENCES CAISSES (Id_Caisse),
    CONSTRAINT FK_OperationsCaisse_Motif FOREIGN KEY (Id_Motif) REFERENCES PARAMETRES_CAISSE (Id_Parametre),
    CONSTRAINT FK_OperationsCaisse_CreePar FOREIGN KEY (Cree_Par) REFERENCES UTILISATEURS (Id_Utilisateur),
    CONSTRAINT FK_OperationsCaisse_ModifiePar FOREIGN KEY (Modifie_Par) REFERENCES UTILISATEURS (Id_Utilisateur),
    CONSTRAINT FK_OperationsCaisse_ValidePar FOREIGN KEY (Valide_Par) REFERENCES UTILISATEURS (Id_Utilisateur),
    CONSTRAINT FK_OperationsCaisse_ComptabilisePar FOREIGN KEY (Comptabilise_Par) REFERENCES UTILISATEURS (Id_Utilisateur),
    CONSTRAINT CK_OperationsCaisse_Type CHECK (Type_Operation IN ('ALIMENTATION', 'DEPENSE', 'REMBOURSEMENT')),
    CONSTRAINT CK_OperationsCaisse_Sens CHECK (Sens_Solde IN ('ENTREE', 'SORTIE')),
    CONSTRAINT CK_OperationsCaisse_Statut CHECK (Statut IN ('BROUILLON', 'VALIDE', 'COMPTABILISE', 'ANNULE')),
    CONSTRAINT CK_OperationsCaisse_Montant CHECK (Montant > 0)
);
CREATE INDEX IX_OperationsCaisse_Caisse ON OPERATIONS_CAISSE (Id_Caisse);
CREATE INDEX IX_OperationsCaisse_Statut ON OPERATIONS_CAISSE (Statut);
CREATE INDEX IX_OperationsCaisse_Projet ON OPERATIONS_CAISSE (Projet);
CREATE INDEX IX_OperationsCaisse_Responsable ON OPERATIONS_CAISSE (Responsable);
CREATE INDEX IX_OperationsCaisse_Date ON OPERATIONS_CAISSE (Date_Operation);
GO

-- ----------------------------------------------------------------------------
-- 5. JUSTIFICATIFS_CAISSE
-- ----------------------------------------------------------------------------
CREATE TABLE JUSTIFICATIFS_CAISSE (
    Id_Justificatif   INT IDENTITY(1,1) PRIMARY KEY,
    Id_Operation      INT           NOT NULL,
    Nom_Fichier       VARCHAR(255)  NOT NULL,
    Chemin_Fichier    VARCHAR(500)  NOT NULL,
    Type_Fichier      VARCHAR(10)   NOT NULL,
    Taille_Octets     INT           NOT NULL,
    Supprime          BIT           NOT NULL DEFAULT 0,   -- suppression logique uniquement
    Date_Ajout        DATETIME      NOT NULL DEFAULT GETDATE(),
    Ajoute_Par        INT           NOT NULL,
    CONSTRAINT FK_Justificatifs_Operation FOREIGN KEY (Id_Operation) REFERENCES OPERATIONS_CAISSE (Id_Operation),
    CONSTRAINT FK_Justificatifs_AjoutePar FOREIGN KEY (Ajoute_Par) REFERENCES UTILISATEURS (Id_Utilisateur),
    CONSTRAINT CK_Justificatifs_Type CHECK (Type_Fichier IN ('PDF', 'JPG', 'PNG'))
);
CREATE INDEX IX_Justificatifs_Operation ON JUSTIFICATIFS_CAISSE (Id_Operation);
GO

-- ----------------------------------------------------------------------------
-- 6. VALIDATIONS_CAISSE
-- Historique des actions de workflow (une ligne par action, jamais modifiee).
-- ----------------------------------------------------------------------------
CREATE TABLE VALIDATIONS_CAISSE (
    Id_Validation   INT IDENTITY(1,1) PRIMARY KEY,
    Id_Operation    INT           NOT NULL,
    Action          VARCHAR(20)   NOT NULL,
    Utilisateur     INT           NOT NULL,
    Date_Action     DATETIME      NOT NULL DEFAULT GETDATE(),
    Commentaire     VARCHAR(500)  NULL,
    CONSTRAINT FK_Validations_Operation FOREIGN KEY (Id_Operation) REFERENCES OPERATIONS_CAISSE (Id_Operation),
    CONSTRAINT FK_Validations_Utilisateur FOREIGN KEY (Utilisateur) REFERENCES UTILISATEURS (Id_Utilisateur),
    CONSTRAINT CK_Validations_Action CHECK (Action IN ('VALIDATION', 'ANNULATION', 'COMPTABILISATION', 'REMISE_BROUILLON'))
);
CREATE INDEX IX_Validations_Operation ON VALIDATIONS_CAISSE (Id_Operation);
GO

-- ----------------------------------------------------------------------------
-- 7. HISTORIQUE_CAISSE
-- Tracabilite champ par champ des modifications (avant/apres), jamais modifiee.
-- ----------------------------------------------------------------------------
CREATE TABLE HISTORIQUE_CAISSE (
    Id_Historique       INT IDENTITY(1,1) PRIMARY KEY,
    Id_Operation        INT           NOT NULL,
    Champ_Modifie       VARCHAR(50)   NOT NULL,
    Ancienne_Valeur     VARCHAR(500)  NULL,
    Nouvelle_Valeur     VARCHAR(500)  NULL,
    Utilisateur         INT           NOT NULL,
    Date_Modification   DATETIME      NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_Historique_Operation FOREIGN KEY (Id_Operation) REFERENCES OPERATIONS_CAISSE (Id_Operation),
    CONSTRAINT FK_Historique_Utilisateur FOREIGN KEY (Utilisateur) REFERENCES UTILISATEURS (Id_Utilisateur)
);
CREATE INDEX IX_Historique_Operation ON HISTORIQUE_CAISSE (Id_Operation);
GO

-- ----------------------------------------------------------------------------
-- 8. CORRESPONDANCE_REGLEMENTS
-- Lien FUTUR entre une operation applicative et un vrai reglement Sage.
-- Non utilisee en mode autonome (recommande pour commencer) - prevue pour un
-- eventuel "mode integre Sage" etudie separement (rappel du prompt).
-- ----------------------------------------------------------------------------
CREATE TABLE CORRESPONDANCE_REGLEMENTS (
    Id_Correspondance      INT IDENTITY(1,1) PRIMARY KEY,
    Id_Operation           INT           NOT NULL,
    RG_No_Sage             INT           NULL,   -- = F_CREGLEMENT.RG_No, si jamais utilise
    EC_No_Sage             INT           NULL,   -- = F_ECRITUREC.EC_No, si jamais utilise
    Statut_Correspondance  VARCHAR(20)   NOT NULL DEFAULT 'NON_LIE',
    Date_Mise_A_Jour       DATETIME      NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_CorrespondanceReglements_Operation UNIQUE (Id_Operation),
    CONSTRAINT FK_CorrespondanceReglements_Operation FOREIGN KEY (Id_Operation) REFERENCES OPERATIONS_CAISSE (Id_Operation),
    CONSTRAINT CK_CorrespondanceReglements_Statut CHECK (Statut_Correspondance IN ('NON_LIE', 'LIE', 'ERREUR'))
);
GO
