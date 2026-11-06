"""
Fixtures partagées - Phase 4.

La base réelle SAGE_CAISSE_APP existe déjà (créée en Phase 3, vérifiée),
mais aucun compte applicatif dédié n'y a encore été créé (en attente,
comme pour CONNECTEUR_SAGE_SHOPIFY dans sage_to_shopify). En attendant,
les tests des services utilisent une base SQLite en mémoire qui partage
EXACTEMENT les mêmes modèles SQLAlchemy (modeles/) - donc la même
structure de colonnes/contraintes - ce qui valide réellement la logique
des services, pas seulement des valeurs de retour simulées.
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import connexion.connexion_app as connexion_app
from config import configuration
from modeles import Base
from services import (
    service_caisses,
    service_justificatifs,
    service_operations,
    service_parametres,
    service_pdf,
    service_utilisateurs,
)

# Chaque service fait "from connexion.connexion_app import obtenir_session" :
# il faut donc patcher le nom importé dans CHAQUE module, pas seulement
# l'attribut du module connexion_app (un "from ... import" copie la
# référence, il ne la relie pas dynamiquement au module d'origine).
_MODULES_A_PATCHER = [
    connexion_app, service_caisses, service_operations, service_parametres,
    service_utilisateurs, service_justificatifs, service_pdf,
]


@pytest.fixture
def session_app(monkeypatch):
    """Fournit une session SQLAlchemy sur une base SQLite en mémoire, fraîche à chaque test."""
    # StaticPool + check_same_thread=False : une SEULE connexion partagée,
    # nécessaire car FastAPI/Starlette exécute les routes synchrones dans
    # un thread différent de celui du test (sinon chaque thread verrait
    # une base ":memory:" SQLite vide et distincte - piège classique).
    moteur = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(moteur)
    FabriqueSession = sessionmaker(bind=moteur)

    for module in _MODULES_A_PATCHER:
        monkeypatch.setattr(module, "obtenir_session", lambda: FabriqueSession())

    session = FabriqueSession()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def mode_ecriture_active_par_defaut():
    """
    Les tests de CRUD/workflow doivent pouvoir écrire par défaut - le
    mode lecture seule (voir droits.verifier_ecriture_autorisee(),
    Phase 5) est donc désactivé en mémoire avant chaque test, puis
    remis à "non défini" après (pour ne pas polluer les autres tests -
    voir config/configuration.py: definir_mode_lecture_seule()).
    Un test qui veut spécifiquement vérifier le blocage doit appeler
    definir_mode_lecture_seule(True) lui-même.
    """
    configuration.definir_mode_lecture_seule(False)
    yield
    configuration._dernier_choix_utilisateur = None
