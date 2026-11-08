"""
Tests de l'API REST (FastAPI) - Phase 4. Utilise la même base SQLite en
mémoire que les tests de services (fixture session_app), pour vérifier
réellement le chemin complet requête HTTP -> service -> base -> réponse.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_creer_et_lister_utilisateur_via_api(session_app):
    reponse = client.post("/utilisateurs", json={
        "login": "dburon", "mot_de_passe": "MotDePasse123!", "nom_complet": "Dorine Buron", "role": "MANAGER",
    })
    assert reponse.status_code == 200
    assert reponse.json()["succes"] is True

    reponse = client.get("/utilisateurs")
    assert reponse.status_code == 200
    assert len(reponse.json()["resultats"]) == 1


def test_creer_operation_via_api_rejette_montant_negatif(session_app):
    client.post("/utilisateurs", json={"login": "test", "mot_de_passe": "x", "nom_complet": "Test"})
    client.post("/caisses", json={"code_caisse": "CA-1", "nom_caisse": "Caisse 1", "societe": "Bijou SA"})

    reponse = client.post("/operations", json={
        "type_operation": "DEPENSE", "id_caisse": 1, "date_operation": "2026-01-01T10:00:00",
        "montant": -5, "cree_par": 1,
    })
    # Rejeté par Pydantic (gt=0) avant même d'atteindre le service -> 422
    assert reponse.status_code == 422


def test_creer_operation_via_api_rejette_remboursement_sans_sens(session_app):
    client.post("/utilisateurs", json={"login": "test", "mot_de_passe": "x", "nom_complet": "Test"})
    client.post("/caisses", json={"code_caisse": "CA-1", "nom_caisse": "Caisse 1", "societe": "Bijou SA"})

    reponse = client.post("/operations", json={
        "type_operation": "REMBOURSEMENT", "id_caisse": 1, "date_operation": "2026-01-01T10:00:00",
        "montant": 30, "cree_par": 1,
    })
    # Rejeté par le service (règle métier) -> 400, via le gestionnaire d'erreur centralisé
    assert reponse.status_code == 400
    assert "remboursement" in reponse.json()["detail"].lower()


def test_cycle_complet_operation_via_api(session_app):
    client.post("/utilisateurs", json={"login": "test", "mot_de_passe": "x", "nom_complet": "Test"})
    manager = client.post("/utilisateurs", json={"login": "manager", "mot_de_passe": "x", "nom_complet": "Manager", "role": "MANAGER"})
    id_manager = manager.json()["id"]
    client.post("/caisses", json={"code_caisse": "CA-1", "nom_caisse": "Caisse 1", "societe": "Bijou SA"})

    creation = client.post("/operations", json={
        "type_operation": "DEPENSE", "id_caisse": 1, "date_operation": "2026-01-01T10:00:00",
        "montant": 45.90, "cree_par": 1, "projet": "Déplacement Lyon",
    })
    assert creation.status_code == 200
    id_operation = creation.json()["id"]

    lecture = client.get(f"/operations/{id_operation}")
    assert lecture.status_code == 200
    assert lecture.json()["donnees"]["Projet"] == "Déplacement Lyon"

    modification = client.put(f"/operations/{id_operation}", json={"utilisateur_id": 1, "montant": 50})
    assert modification.status_code == 200

    liste = client.get("/operations", params={"projet": "Déplacement Lyon"})
    assert liste.status_code == 200
    assert len(liste.json()["resultats"]) == 1

    # Suppression directe réservée au MANAGER (prmopt_3.txt) - le créateur (USER) seul est refusé.
    suppression_refusee = client.delete(f"/operations/{id_operation}", params={"utilisateur_id": 1, "confirmer": True})
    assert suppression_refusee.status_code == 400

    suppression = client.delete(f"/operations/{id_operation}", params={"utilisateur_id": id_manager, "confirmer": True})
    assert suppression.status_code == 200
