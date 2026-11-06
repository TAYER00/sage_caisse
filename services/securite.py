"""
Hachage des mots de passe utilisateurs - jamais stockés en clair (règle du
prompt, section "SECURITE ET TRACABILITE").

PBKDF2-HMAC-SHA256 avec sel aléatoire par utilisateur (module standard
`hashlib`, pas de dépendance supplémentaire) - 200 000 itérations,
recommandation OWASP actuelle pour PBKDF2-SHA256.
"""

import hashlib
import secrets

_ITERATIONS = 200_000


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Objectif : transformer un mot de passe en clair en une chaîne sûre à
    stocker en base (jamais le mot de passe lui-même).

    Retour : chaîne au format "sel_hex$hash_hex".

    Exemple :
        hacher_mot_de_passe("MonMotDePasse123!")
    """
    sel = secrets.token_hex(16)
    hache = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), bytes.fromhex(sel), _ITERATIONS)
    return f"{sel}${hache.hex()}"


def verifier_mot_de_passe(mot_de_passe: str, hache_stocke: str) -> bool:
    """
    Objectif : vérifier qu'un mot de passe en clair correspond au hash stocké.

    Retour : True si le mot de passe est correct.

    Exemple :
        verifier_mot_de_passe("MonMotDePasse123!", utilisateur.Mot_De_Passe_Hash)
    """
    try:
        sel, hache_attendu = hache_stocke.split("$", 1)
    except ValueError:
        return False
    hache_calcule = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode("utf-8"), bytes.fromhex(sel), _ITERATIONS)
    return secrets.compare_digest(hache_calcule.hex(), hache_attendu)
