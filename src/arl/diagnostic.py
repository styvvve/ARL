"""Vérifie l'environnement : Python, configuration, dossier de notes, traces, Ollama, modèle.

Rien n'est envoyé sur Internet : seul le serveur Ollama configuré (localhost par défaut) est interrogé.
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
import urllib.error
import urllib.request
from pathlib import Path
from shutil import disk_usage

from arl import config
from arl.errors import ConfigurationError


def ollama_models(url: str) -> list[str] | None:
    """Renvoie la liste des modèles installés, ou None si Ollama ne répond pas."""
    try:
        with urllib.request.urlopen(f"{url}/api/tags", timeout=3) as response:
            return [m["name"] for m in json.load(response).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return None


def _writable(directory: Path) -> bool:
    """Le dossier existe et est inscriptible, ou peut être créé (son parent existant l'est)."""
    directory = directory.resolve()
    while not directory.exists():
        directory = directory.parent
    return os.access(directory, os.W_OK)


def execute() -> int:
    ok = True
    print(f"Python        : {platform.python_version()}", end="")
    if sys.version_info < (3, 10):
        print("  -> ÉCHEC : Python 3.10 ou plus récent est requis.")
        ok = False
    else:
        print("  -> OK")

    try:
        settings = config.load()
        print(f"Configuration : OK (fournisseur {settings.supplier}, consigne {settings.instruction})")
    except ConfigurationError as exc:
        print(f"Configuration : ÉCHEC : {exc} -> diagnostic poursuivi avec les valeurs par défaut")
        settings = config.Settings()
        ok = False

    count = len(list(settings.notes_dir.glob("*.md")))
    print(f"Notes         : {count} fichier(s) dans {settings.notes_dir}", "-> OK" if count else "-> ÉCHEC")
    ok &= count > 0

    traces_ok = _writable(settings.traces_dir)
    print(f"Traces        : {settings.traces_dir.resolve()}",
          "-> OK" if traces_ok else "-> ÉCHEC : dossier non inscriptible")
    ok &= traces_ok

    print(f"Disque libre  : {disk_usage(Path.home()).free / 1024**3:.1f} Go")

    if importlib.util.find_spec("openai") is None:
        print("Paquet openai : absent -> `pip install -e .` dans le venv du projet")
        ok = False
    else:
        print("Paquet openai : OK")

    models = ollama_models(settings.ollama_url)
    if models is None:
        print(f"Ollama        : aucun serveur sur {settings.ollama_url} -> lance l'application Ollama "
              "ou `ollama serve` (non bloquant pour les modules 1 et 2)")
    else:
        print(f"Ollama        : OK, {len(models)} modèle(s) : {', '.join(models) or 'aucun'}")
        if settings.model not in models:
            print(f"Modèle        : {settings.model} absent -> `ollama pull {settings.model}`")
    print("\nDiagnostic :", "prêt" if ok else "à corriger")
    return 0 if ok else 1
