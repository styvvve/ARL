from __future__ import annotations

import ast
import operator
import os
import re
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_NOTES = Path(os.getenv("ARL_DOSSIER_NOTES", RACINE / "data" / "notes")).resolve()
TAILLE_MAX = 4000 #protege le contexte

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg, ast.UAdd: operator.pos}

def _evaluer(noeud: ast.AST) -> float:
    if isinstance(noeud, ast.Constant) and isinstance(noeud.value, (int, float)):
        return noeud.value
    if isinstance(noeud, ast.BinOp) and type(noeud.op) in _OPS:
        left, right = _evaluer(noeud.left), _evaluer(noeud.right)
        if isinstance(noeud.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exposant trop grand")
        return _OPS[type(noeud.op)](left, right)
    if isinstance(noeud, ast.UnaryOp) and type(noeud.op) in _OPS:
        return _OPS[type(noeud.op)](_evaluer(noeud.operand))    if isinstance(noeud, ast.Num):
        raise ValueError(f"'{noeud.n}' n'est pas un nombre ; remplace le par sa valeur réelle"
                         f"(trouve la d'abord avec rechercher_notes ou lire_note).")
    raise ValueError(f"élément non autorisé : {type(noeud).__name__}")


def calculer(expression: str) -> str:
    """Évalue une expression arithmétique (+ - * / ** % et parenthèses)."""
    if len(expression) > 200:
        return "ERREUR: expression trop longue (200 caractères max)"
    try:
        resultat = _evaluer(ast.parse(expression.replace(",", "."), mode="eval").body)
    except ZeroDivisionError:
        return "ERREUR: division par zéro"
    except (ValueError, SyntaxError) as exc:
        return f"ERREUR: expression invalide ({exc})"
    resultat = round(resultat, 6)
    return str(int(resultat)) if float(resultat).is_integer() else str(resultat)


def lister_notes() -> str:
    """Liste les notes disponibles."""
    noms = sorted(p.name for p in DOSSIER_NOTES.glob("*.md"))
    return "\n".join(noms) if noms else "Aucune note."


def _chemin_sur(nom: str) -> Path | None:
    """Renvoie le chemin de la note si et seulement s'il est DANS le dossier de notes."""
    if "/" in nom or "\\" in nom or not nom.endswith(".md"):
        return None
    chemin = (DOSSIER_NOTES / nom).resolve()
    return chemin if chemin.parent == DOSSIER_NOTES and chemin.is_file() else None


def lire_note(nom: str) -> str:
    """Lit une note ; refuse tout chemin hors du dossier de notes."""
    chemin = _chemin_sur(nom)
    if chemin is None:
        return f"ERREUR: note introuvable ou nom invalide : {nom}. Utilise lister_notes."
    return chemin.read_text(encoding="utf-8")[:TAILLE_MAX]


def _plat(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower()


def rechercher_notes(requete: str) -> str:
    """Cherche des mots-clés dans les notes ; renvoie au plus 5 notes avec un extrait."""
    mots = [m for m in re.findall(r"\w{3,}", _plat(requete))][:8]
    if not mots:
        return "ERREUR: requête vide ; donne un ou plusieurs mots-clés."
    scores = []
    for chemin in DOSSIER_NOTES.glob("*.md"):
        texte = chemin.read_text(encoding="utf-8")
        plat = _plat(texte)
        score = sum(plat.count(m) for m in mots) + 3 * sum(m in _plat(chemin.name) for m in mots) #ranking heuristic
        if score:
            pos = min((plat.find(m) for m in mots if m in plat), default=0)
            extrait = " ".join(texte[max(0, pos - 60): pos + 140].split())
            scores.append((score, chemin.name, extrait))
    if not scores:
        return "Aucune note ne contient ces mots-clés."
    scores.sort(key=lambda x: (-x[0], x[1]))
    return "\n".join(f"{nom} (score {s}) : …{extrait}…" for s, nom, extrait in scores[:5])


REGISTRE = {"lister_notes": lister_notes, "lire_note": lire_note,
            "rechercher_notes": rechercher_notes, "calculer": calculer}


def _schema(nom: str, description: str, parametres: dict | None = None) -> dict:
    proprietes = {k: {"type": "string", "description": v} for k, v in (parametres or {}).items()}
    return {"type": "function", "function": {
        "name": nom, "description": description,
        "parameters": {"type": "object", "properties": proprietes, "required": list(proprietes)}}}


SCHEMAS = [
    _schema("rechercher_notes", "Cherche des mots-clés dans toutes les notes et renvoie les noms "
        "des notes pertinentes avec un extrait. À utiliser en premier quand tu ne sais pas "
        "quelle note lire.", {"requete": "mots-clés, ex. 'budget Beta'"}),
    _schema("lire_note", "Renvoie le contenu complet d'une note. Nom exact requis, "
        "ex. 'projet-alpha.md'.", {"nom": "nom de fichier se terminant par .md"}),
    _schema("lister_notes", "Liste les noms de toutes les notes disponibles."),
    _schema("calculer", "Calcule une expression arithmétique, ex. '1200*1.2'. Utilise-le pour "
        "TOUT calcul au lieu de calculer de tête.", {"expression": "expression arithmétique"}),
]
def executer_outil(nom: str, arguments: dict) -> str:
    """Point d'exécution unique : liste blanche + capture des erreurs d'arguments."""
    fonction = REGISTRE.get(nom)
    if fonction is None:
        return f"ERREUR: outil inconnu '{nom}'. Outils disponibles : {', '.join(REGISTRE)}"
    try:
        return fonction(**arguments)
    except TypeError as exc:
        return f"ERREUR: arguments invalides pour {nom} ({exc})"