from __future__ import annotations

import argparse
import json
import sys

from arl import MILESTONE, config, diagnostic, prompts
from arl.agent import Agent, Result
from arl.errors import ARLError
from arl.report import Report
from arl.llm import create_client
from arl.notes import NotesRepository
from arl.tools import ToolBox


def build_agent(settings: config.Settings, display: bool = True) -> Agent:
    return Agent(client=create_client(settings), tools=ToolBox(NotesRepository(settings.notes_dir)),
                 report=Report(settings.traces_dir), instruction=settings.instruction,
                 max_step=settings.max_step, context_budget=settings.context_budget,
                 display=display)


def display_result(r: Result) -> None:
    print("\nRéponse :", r.response)
    v = r.verification
    state = "vérifiée" if v["valid"] else "À VÉRIFIER : " + " ; ".join(v["problems"])
    print(f"({r.status}, {len(r.steps)} étape(s), {r.duration_s:.1f} s, sources {v['citations'] or 'aucune'}, "
          f"{state}, trace {r.id})")


def chat(agent: Agent, memory_size: int) -> int:
    """Mémoire courte : on renvoie au modèle les derniers échanges (questions + réponses finales)."""
    history: list[dict] = []
    print("Conversation (ligne vide pour quitter).")
    while True:
        try:    
            question = input("\nToi > ").strip()
        except EOFError:
            break
        if not question:
            break
        r = agent.answer(question, history=history[-2 * memory_size:])
        display_result(r)
        history += [{"role": "user", "content": question}, {"role": "assistant", "content": r.response}]
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="arl", description=f"Agent Reliability Lab ({MILESTONE})")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("diagnostic", help="vérifier l'environnement")
    subparsers.add_parser("config", help="afficher la configuration effective (secrets masqués)")
    p = subparsers.add_parser("demander", help="poser une question à l'assistant")
    p.add_argument("question")
    p.add_argument("--sans-outils", dest="without_tools", action="store_true", help="appel simple, sans outils (jalon J1)")
    p = subparsers.add_parser("discuter", help="conversation avec mémoire courte")
    p.add_argument("--memoire", dest="memory", type=int, default=3, help="nombre d'échanges conservés")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    if args.command == "diagnostic":
        return diagnostic.execute()
    settings = config.load()
    if args.command == "config":
        print(json.dumps(settings.description(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "demander" and args.without_tools:
        client = create_client(settings)
        output = client.complete([{"role": "system", "content": "Réponds en français, brièvement."},
                                  {"role": "user", "content": args.question}], [])
        print(output.content, f"\n({client.model}, {output.latency_s:.1f} s)")
        return 0
    agent = build_agent(settings)
    if args.command == "demander":
        display_result(agent.answer(args.question))
        return 0
    if args.command == "discuter":
        return chat(agent, args.memory)
    return 1


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except ARLError as exc:  # erreurs attendues : message clair, pas de trace Python
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
