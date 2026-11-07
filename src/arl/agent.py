from __future__ import annotations

import os
import time

from openai import OpenAI, NotFoundError


BASE_URL = os.getenv("ARL_OLLAMA_URL", "http://localhost:11434") + "/v1"
MODELE = os.getenv("ARL_MODELE", "qwen3:4b")
CONSIGNE = "Tu es l'assistant de notes de l'équipe. Réponds en français brièvement."

def demander_simple(question: str, historique: list[dict] | None = None) -> tuple[str, float]:
    """Envoie une question (et éventuellement un historique) ; renvoie (réponse, durée)."""
    client = OpenAI(base_url=BASE_URL, api_key="ollama")
    messages = [{"role": "system", "content": CONSIGNE},
                *(historique or []),
                {"role": "user", "content": question}]
    debut = time.perf_counter()
    try:
        #temperature=0; il choisit toujours la meme chose
        response = client.chat.completions.create(model=MODELE, messages=messages, temperature=0)
    except NotFoundError as e:
        print("URL :", e.request.url)
        print("Modèle :", MODELE)
        print("Réponse :", e.response.text)
        raise
    return response.choices[0].message.content or "", time.perf_counter() - debut