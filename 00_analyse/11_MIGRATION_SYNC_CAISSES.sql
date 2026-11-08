-- Migration Phase 11 (prompt_4.txt) - synchronisation des caisses depuis BIJOU.
-- A exécuter sur SAGE_CAISSE_APP uniquement (jamais sur BIJOU).
-- Additive uniquement : nouvelle colonne nullable + contrainte UNIQUE sur une
-- colonne déjà existante (SQL Server autorise plusieurs NULL sous UNIQUE,
-- donc les caisses sans lien Sage ne sont pas impactées). Aucune donnée
-- existante n'est supprimée ni modifiée par ce script.

ALTER TABLE CAISSES ADD Derniere_Synchro_Sage DATETIME NULL;

ALTER TABLE CAISSES ADD CONSTRAINT UQ_Caisses_NumeroCaisseSage UNIQUE (Numero_Caisse_Sage);
