"""Interface en ligne de commande : `arl <commande>`."""
from __future__ import annotations

import argparse

from arl import JALON, diagnostic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arl", description=f"Agent Reliability Lab ({JALON})")
    sous = parser.add_subparsers(dest="commande", required=True)
    sous.add_parser("diagnostic", help="vérifier l'environnement")
    args = parser.parse_args(argv)
    if args.commande == "diagnostic":
        return diagnostic.execute()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
