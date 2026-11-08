from __future__ import annotations

import json
import uuid
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

from arl import citations, prompts
from arl.llm import LLMClient
from arl.tools import ToolBox
from arl.report import Report

MAX_REMINDERS = 1
REMINDER = ("Tu n'as lu aucune note : ta réponse n'est pas vérifiable. "
            "Appelle d'abord rechercher_notes, puis lire_note, puis réponds en citant la note.")  # Précision accrue car les petits modèles ont l'habitude de skip
REMOVED = "[observation retirée pour respecter le budget de contexte]"


@dataclass
class Result:
    id: str
    date: str
    model: str
    instruction: str
    instruction_footprint: str
    question: str
    response: str = ""
    status: str = "limite_etapes"
    steps: list[dict] = field(default_factory=list)
    notes_read: list[str] = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    entry_token: int = 0
    exit_token: int = 0
    duration_s: float = 0.0


def estimate_token(messages: list[dict]) -> int:
    """Estimation grossière : environ 4 caractères par token. Suffisant pour un garde-fou."""
    return len(json.dumps(messages, ensure_ascii=False, default=str)) // 4


def compact(messages: list[dict], budget: int) -> int:
    """Remplace les plus anciennes observations d'outils tant que le budget est dépassé.
    Garde toujours la consigne, la question et les deux dernières observations.
    Renvoie le nombre d'observations retirées."""
    removed = 0
    for m in [m for m in messages if m.get("role") == "tool"][:-2]:
        if estimate_token(messages) <= budget:
            break
        if m["content"] != REMOVED:
            m["content"], removed = REMOVED, removed + 1
    return removed

class Agent:
    def __init__(self, client: LLMClient, tools: ToolBox, report: Report | None = None,
                 instruction: str = prompts.DEFAULT_VERSION, max_step: int = 6,
                 context_budget: int = 6000, display: bool = True):
        self.client, self.tools = client, tools
        self.report = report or Report(None)
        self.instruction, self.max_step = instruction, max_step
        self.context_budget, self.display = context_budget, display

    def answer(self, question: str, history: list[dict] | None = None) -> Result:

        r = Result(id=uuid.uuid4().hex[:8], date=datetime.now().isoformat(timespec="seconds"),
                     model=self.client.model, instruction=self.instruction,
                     instruction_footprint=prompts.footprint(self.instruction), question=question,
                     response="ARRÊT : nombre maximal d'étapes atteint.")
        messages = [{"role": "system", "content": prompts.instructions(self.instruction)},
                    *(history or []), {"role": "user", "content": question}]
        notes_read: dict[str, str] = {}
        observations: list[str] = []
        reminders = 0 # garde fou pour éviter qu'il n'arrête avant de lire au moins une fois les notes
        start = time.perf_counter()
        for number in range(1, self.max_step + 1):
            removed = compact(messages, self.context_budget)
            output = self.client.complete(messages, self.tools.schemas())
            messages.append(output.message)  # message COMPLET renvoyé ensuite
            r.entry_token += output.entry_token or 0
            r.exit_token += output.exit_token or 0
            step = {"step_number": number, "latency_s": output.latency_s, "removed_observations": removed,
                     "entry_token": output.entry_token, "exit_token": output.exit_token,
                     "calls": []}
            r.steps.append(step)
            if not output.calls:  # DÉCISION : le modèle a fini
                missing = prompts.MISSING_MARKER.rstrip(".").lower() in output.content.lower()
                # garde fou pour s'il donne une rep sans aucune note lue -> relance
                if not notes_read and not missing and reminders < MAX_REMINDERS:
                    reminders += 1
                    step["reminder"] = True
                    messages.append({"role": "user", "content": REMINDER}) #reagit mieux quand c'est un user
                    continue
                r.status, r.response = "termine", output.content
                break
            for call in output.calls:  # ACTION puis OBSERVATION
                try:
                    arguments = json.loads(call.raw_arguments or "{}")
                    result = self.tools.execute(call.name, arguments)
                except json.JSONDecodeError:
                    arguments, result = None, "ERREUR: arguments JSON mal formés"
                if call.name == "lire_note" and not result.startswith("ERREUR"):
                    notes_read[arguments["name"]] = result
                observations.append(result)
                step["calls"].append({"tool": call.name, "arguments": arguments,
                                      "result": result[:300]})
                if self.display:
                    print(f"  [outil] {call.name}({arguments}) -> {result[:70]!r}")
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        r.duration_s = round(time.perf_counter() - start, 3)
        missing = prompts.MISSING_MARKER.rstrip(".").lower() in r.response.lower()
        v = citations.verify(r.response, notes_read, observations, question,
                             require_citation=r.status == "termine" and not missing)
        r.notes_read = sorted(notes_read)
        r.verification = {"valid": v.is_valid, "citations": v.citations, "problems": v.problems}
        self.report.write(asdict(r))
        return r
