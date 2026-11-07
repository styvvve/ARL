from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
import os
import time

from openai import OpenAI, NotFoundError
from arl.tools import SCHEMAS, executer_outil


BASE_URL = os.getenv("ARL_OLLAMA_URL", "http://localhost:11434") + "/v1"
MODELE = os.getenv("ARL_MODELE", "qwen3:1.7b")
MAX_ETAPES = int(os.getenv("ARL_MAX_ETAPES", "6"))
DOSSIER_TRACES = Path(os.getenv("ARL_DOSSIER_TRACES", "traces"))

CONSIGNE = "Tu es l'assistant de notes de l'équipe. Réponds en français brièvement."

CONSIGNE_OUTILS = (
    "Tu es l'assistant de notes de l'équipe. Réponds en français, brièvement. "
    "Pour toute information sur l'équipe ou ses projets, utilise les outils : "
    "rechercher_notes, puis lire_note. Pour tout calcul, utilise calculer. "
    "Si un outil renvoie ERREUR, corrige ton appel."
)

def _client() -> OpenAI:
    return OpenAI(base_url=BASE_URL, api_key="ollama")  # clé exigée par le SDK, ignorée par Ollama

def demander_simple(question: str, historique: list[dict] | None = None) -> tuple[str, float]:
    """Envoie une question (et éventuellement un historique) ; renvoie (réponse, durée)."""
    messages = [{"role": "system", "content": CONSIGNE},
                *(historique or []),
                {"role": "user", "content": question}]
    debut = time.perf_counter()
    try:
        #temperature=0; il choisit toujours la meme chose
        response = _client().chat.completions.create(model=MODELE, messages=messages, temperature=0)
    except NotFoundError as e:
        print("URL :", e.request.url)
        print("Modèle :", MODELE)
        print("Réponse :", e.response.text)
        raise
    return response.choices[0].message.content or "", time.perf_counter() - debut

def lancer_agent(question: str, client: OpenAI | None = None, afficher: bool = True) -> dict:
    """Boucle agentique ; renvoie un dict {reponse, etapes, statut} et écrit une trace JSONL."""
    client = client or _client()
    messages = [{"role": "system", "content": CONSIGNE_OUTILS},
                {"role": "user", "content": question}]
    etapes, statut, reponse = [], "limite_etapes", "ARRÊT : nombre maximal d'étapes atteint."
    for numero in range(1, MAX_ETAPES + 1):
        debut = time.perf_counter()
        sortie = client.chat.completions.create(model=MODELE, messages=messages, tools=SCHEMAS)
        message = sortie.choices[0].message
        messages.append(message.model_dump(exclude_none=True)) # message COMPLET renvoyé ensuite
        etape = {"etape": numero, "latence_s": round(time.perf_counter() - debut, 3), "appels": []}
        etapes.append(etape)
        if not message.tool_calls: # DÉCISION : le modèle a fini
            statut, reponse = "termine", message.content or ""
            break
        for appel in message.tool_calls: # ACTION puis OBSERVATION
            try:
                arguments = json.loads(appel.function.arguments or "{}")
                resultat = executer_outil(appel.function.name, arguments)
            except json.JSONDecodeError:
                arguments, resultat = None, "ERREUR: arguments JSON mal formés"
            etape["appels"].append({"outil": appel.function.name, "arguments": arguments,
                                    "resultat": resultat[:300]}) #300 premiers caractères
            if afficher:
                print(f" [outil] {appel.function.name}({arguments}) -> {resultat[:70]!r}")
            messages.append({"role": "tool", "tool_call_id": appel.id, "content": resultat})
    resultat_final = {"id": uuid.uuid4().hex[:8], "date":
                    datetime.now().isoformat(timespec="seconds"),
                    "modele": MODELE, "question": question, "reponse": reponse,
                    "statut": statut, "etapes": etapes}
    DOSSIER_TRACES.mkdir(parents=True, exist_ok=True)
    with open(DOSSIER_TRACES / "traces.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(resultat_final, ensure_ascii=False) + "\n")
    return resultat_final