from __future__ import annotations

import re
from dataclasses import dataclass, field

CITATION_PATTERN = re.compile(r"\[source\s*:\s*([\w.\-]+\.md)\s*\]", re.IGNORECASE)
# milliers séparés par une espace (1 200) OU nombre simple ; décimales avec . ou ,
_NUMBER_PATTERN = re.compile(r"\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


@dataclass
class Verification:
    citations: list[str] = field(default_factory=list) #a default list
    problems: list[str] = field(default_factory=list)

    @property # method into a property
    def is_valid(self) -> bool:
        return not self.problems


def citations(response: str) -> list[str]:
    return list(dict.fromkeys(CITATION_PATTERN.findall(response)))


def _normalize_number(raw: str) -> str:
    n = re.sub(r"[\s  ]", "", raw).replace(",", ".")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n


def numbers(text: str) -> set[str]:
    return {_normalize_number(m) for m in _NUMBER_PATTERN.findall(text)}


def verify(response: str, notes_read: dict[str, str], observations: list[str],
           question: str = "", require_citation: bool = True) -> Verification:
    """notes_lues : {nom: contenu} des notes lues ; observations : résultats bruts des outils ;
    question : les nombres donnés par l'utilisateur (ex. « 20 % ») sont légitimes."""
    v = Verification(citations=citations(response))
    if require_citation and not v.citations:
        v.problems.append("aucune source citée")
    for name in v.citations:
        if name not in notes_read:
            v.problems.append(f"source citée mais non lue pendant l'exécution : {name}")
    without_citations = CITATION_PATTERN.sub("", response)
    support_texts = [
            notes_read.get(n, "") for n in v.citations
    ] + observations + [question]
    support = numbers(" ".join(support_texts))
    for n in sorted(numbers(without_citations)):
        if len(n.split(".")[0]) >= 2 and n not in support: #exclure faux negatif et si un nbre pas dans la liste des nbres suivies par l'agent alors
            v.problems.append(f"nombre non étayé : {n}")
    return v