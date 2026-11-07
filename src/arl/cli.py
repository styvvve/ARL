"""Interface en ligne de commande : `arl <commande>`."""
from __future__ import annotations

import argparse

from arl import JALON, diagnostic, agent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arl", description=f"Agent Reliability Lab ({JALON})")
    sous = parser.add_subparsers(dest="commande", required=True)
    sous.add_parser("diagnostic", help="vérifier l'environnement")
    demander_parser = sous.add_parser("demander", help="Demander quelque chose")
    demander_parser.add_argument("texte", help="la question à poser")
    demander_parser.add_argument("--sans-outils", action="store_true", help="ne pas utiliser les outils")
    args = parser.parse_args(argv)
    if args.commande == "diagnostic":
        return diagnostic.execute()
    elif args.commande == "demander":
        if args.sans_outils:
            texte, duree = agent.demander_simple(args.texte)
            print(texte)
            print(f"({duree:.1f} secondes)")
            return 0
        resultat = agent.lancer_agent(args.texte)
        print("\nRéponse :", resultat["reponse"])
        print(f"({resultat['statut']}, {len(resultat['etapes'])} étape(s), trace {resultat['id']})")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
