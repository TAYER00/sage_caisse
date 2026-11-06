"""
Journalisation applicative (Phase 8).

Trace chaque requête HTTP (méthode, chemin, code de réponse, durée) et
chaque erreur serveur, dans un fichier avec rotation (logs/sage_caisse.log).

Ne journalise JAMAIS le corps des requêtes (mots de passe, données
personnelles) - uniquement les métadonnées techniques de la requête.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

DOSSIER_LOGS = Path(__file__).resolve().parent.parent / "logs"


def obtenir_journal() -> logging.Logger:
    """Retourne le logger applicatif unique, configuré au premier appel."""
    journal = logging.getLogger("sage_caisse")
    if not journal.handlers:
        DOSSIER_LOGS.mkdir(exist_ok=True)
        journal.setLevel(logging.INFO)
        gestionnaire = RotatingFileHandler(
            DOSSIER_LOGS / "sage_caisse.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        gestionnaire.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        journal.addHandler(gestionnaire)
    return journal
