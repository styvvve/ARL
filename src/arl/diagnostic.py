"""Vérifie l'environnement : Python, dossier de notes, serveur Ollama, modèle.

Rien n'est envoyé sur Internet : seul http://localhost:11434 est interrogé.
"""
from __future__ import annotations

import json
import os
import platform
import sys
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
URL_OLLAMA = os.getenv("ARL_OLLAMA_URL", "http://localhost:11434")


def modeles_ollama(url: str = URL_OLLAMA) -> list[str] | None:
    """Renvoie la liste des modèles installés, ou None si Ollama ne répond pas."""
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as rep:
            return [m["name"] for m in json.load(rep).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return None


def execute() -> int:
    ok = True
    print(f"Python        : {platform.python_version()}", end="")
    if sys.version_info < (3, 10):
        print("  -> ÉCHEC : Python 3.10 ou plus récent est requis.")
        ok = False
    else:
        print("  -> OK")
    notes = RACINE / "data" / "notes"
    nb = len(list(notes.glob("*.md")))
    print(f"Notes         : {nb} fichier(s) dans {notes}", "-> OK" if nb else "-> ÉCHEC")
    ok &= nb > 0
    modeles = modeles_ollama()
    if modeles is None:
        print(f"Ollama        : aucun serveur sur {URL_OLLAMA} -> lance l'application Ollama "
              "ou `ollama serve` (non bloquant pour les modules 1 et 2)")
    else:
        print(f"Ollama        : OK, {len(modeles)} modèle(s) : {', '.join(modeles) or 'aucun'}")
        voulu = os.getenv("ARL_MODELE", "qwen3:4b")
        if voulu not in modeles:
            print(f"Modèle        : {voulu} absent -> `ollama pull {voulu}`")
    print("\nDiagnostic :", "prêt" if ok else "à corriger")
    return 0 if ok else 1
