from __future__ import annotations

import ast
import operator
from typing import Callable
from dataclasses import dataclass

from arl.notes import NotesRepository

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg, ast.UAdd: operator.pos}

def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exposant trop grand")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Name):
        raise ValueError(f"'{node.id}' n'est pas un nombre ; remplace le par sa valeur réelle "
                         f"(trouve la d'abord avec rechercher_notes ou lire_note).")
    raise ValueError(f"élément non autorisé : {type(node).__name__}")


def calculate(expression: str) -> str:
    """Évalue une expression arithmétique (+ - * / ** % et parenthèses)."""
    if len(expression) > 200:
        return "ERREUR: expression trop longue (200 caractères max)"
    try:
        result = _evaluate(ast.parse(expression.replace(",", "."), mode="eval").body)
    except ZeroDivisionError:
        return "ERREUR: division par zéro"
    except (ValueError, SyntaxError) as exc:
        return f"ERREUR: expression invalide ({exc})"
    result = round(result, 6)
    return str(int(result)) if float(result).is_integer() else str(result)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, str]          # nom du paramètre -> description (tous des chaînes)
    function: Callable[..., str]
    level: str = "lecture"             # « lecture » ou « ecriture »

    def schema(self) -> dict:
        properties = {k: {"type": "string", "description": v} for k, v in self.parameters.items()}
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": {"type": "object", "properties": properties, "required": list(properties)}}}


class ToolBox:
    def __init__(self, repository: NotesRepository):
        self.repository = repository
        self.tools: dict[str, Tool] = {}
        for tool in (
            Tool("rechercher_notes", "Cherche des mots-clés dans toutes les notes et renvoie les noms "
                  "des notes pertinentes avec un extrait. À utiliser en premier quand tu ne sais pas "
                  "quelle note lire.", {"query": "mots-clés tirés de la question"}, self._search),
            # Exemples volontairement neutres : un exemple tiré des vraies notes (nom, montant)
            # est recopié tel quel par les petits modèles, qui répondent alors sans appeler d'outil.
            Tool("lire_note", "Renvoie le contenu complet d'une note. Nom exact requis, tel que "
                  "renvoyé par rechercher_notes.", {"name": "nom de fichier se terminant par .md"}, self._read),
            Tool("lister_notes", "Liste les noms de toutes les notes disponibles.", {}, self._list),
            Tool("calculer", "Calcule une expression arithmétique, ex. '(3+4)*2'. Utilise-le pour "
                  "TOUT calcul au lieu de calculer de tête.", {"expression": "expression arithmétique"},
                  calculate),
        ):
            self.add(tool)

    def add(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def schemas(self) -> list[dict]:
        return [tool.schema() for tool in self.tools.values()]

    def execute(self, name: str, arguments: dict) -> str:
        """Point d'exécution unique : liste blanche + validation des arguments."""
        tool = self.tools.get(name)
        if tool is None:
            return f"ERREUR: outil inconnu '{name}'. Outils disponibles : {', '.join(self.tools)}"
        if not isinstance(arguments, dict) or set(arguments) != set(tool.parameters) \
                or not all(isinstance(v, str) for v in arguments.values()):
            return f"ERREUR: arguments invalides pour {name} ; attendu : {list(tool.parameters) or 'aucun'}"
        return tool.function(**arguments)

    # --- adaptateurs vers le dépôt (le stockage reste dans notes.py) ---
    def _list(self) -> str:
        return "\n".join(self.repository.list()) or "Aucune note."

    def _read(self, name: str) -> str:
        text = self.repository.read(name)
        return text if text is not None else \
            f"ERREUR: note introuvable ou nom invalide : {name}. Utilise rechercher_notes ou lister_notes."

    def _search(self, query: str) -> str:
        if not query.strip():
            return "ERREUR: requête vide ; donne un ou plusieurs mots-clés."
        results = self.repository.search(query)
        if not results:
            return "Aucune note ne contient ces mots-clés."
        return "\n".join(f"{name} (score {score}) : …{extract}…" for name, score, extract in results)
