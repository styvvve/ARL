from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol


from arl.errors import SupplierError, ConfigurationError


@dataclass
class ToolCall:
    id: str
    name: str
    raw_arguments: str


@dataclass
class LLMResponse:
    message: dict
    content: str
    calls: list[ToolCall] = field(default_factory=list)
    entry_token: int | None = None
    exit_token: int | None = None
    latency_s: float = 0.0


class LLMClient(Protocol):
    model: str
    local: bool

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


class OpenAICompatibleClient:
    """Tout service qui parle format << chat completions >> d'OpenAI : Ollama(/v1), API distantes"""

    def __init__(self, base_url: str, key: str, model: str, local: bool, options: dict | None = None):
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=key)
        self.model, self.local, self.options = model, local, options or {}

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        import openai
        start = time.perf_counter()
        try:
            response = self.client.chat.completions.create(model=self.model, messages=messages, tools=tools or None, **self.options)
        except openai.APIConnectionError as exc:
            raise SupplierError(f"Impossible de se connecter au service ({exc.__class__.__name__})") from exc
        except openai.APIStatusError as exc:
            raise SupplierError(f"Le service a refusé la requête ({exc.status_code}) : " f"{str(exc)[:200]}") from exc

        message = response.choices[0].message
        usage = getattr(response, "usage", None)
        return LLMResponse(
            message = message.model_dump(exclude_none=True),
            content = message.content or "",
            calls = [ToolCall(id=call.id, name=call.function.name, raw_arguments=call.function.arguments or "{}") for call in message.tool_calls or []],
            entry_token = getattr(usage, "prompt_tokens", None),
            exit_token = getattr(usage, "completion_tokens", None),
            latency_s = round(time.perf_counter() - start, 3))


class SimulatedClient:
    """Client scripté pour les tests: une fonction décide décide la réponse à partir des messages."""

    def __init__(self, function: Callable[[list[dict], list[dict]], dict], model: str = "simule"):
        self.model, self.function, self.local = model, function, True

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        msg = self.function(messages, tools)
        calls = [ToolCall(a["id"], a["function"]["name"],
                          a["function"]["arguments"])
                 for a in msg.get("tool_calls", [])]
        return LLMResponse(message=msg, content=msg.get("content") or "", calls=calls,
                           entry_token=len(json.dumps(messages)) // 4,
                                exit_token=len(json.dumps(msg)) // 4)


def create_client(settings) -> LLMClient:
    """Fabrique du client à partir des réglages (un seul endroit connaît les fournisseurs)."""
    if settings.supplier == "ollama":
        return OpenAICompatibleClient(f"{settings.ollama_url}/v1", "ollama", settings.model, local=True)
    raise ConfigurationError(f"fournisseur inconnu : {settings.supplier} (disponibles : ollama)")