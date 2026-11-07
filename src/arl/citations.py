from __future__ import annotations

import re
from dataclasses import dataclass, field

MOTIF_CITATION = re.compile(r"\[source\s*:\s*([\w.\-]+\.md)\s*\]", re.IGNORECASE)
# milliers séparés par une espace (1 200) OU nombre simple ; décimales avec . ou ,
_MOTIF_NOMBRE = re.compile(r"\d{1,3}(?:[  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


@dataclass
class Verification:
    citations: list[str] = field(default_factory=list) #a default list
    problems: list[str] = field(default_factory=list)

    @property # method into a property
    def valide(self) -> bool:
        return not self.problems


def citations(reponse: str) -> list[str]:
    return list(dict.fromkeys(MOTIF_CITATION.findall(reponse)))


def _normaliser_nombre(brut: str) -> str:
    n = re.sub(r"[\s  ]", "", brut).replace(",", ".")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n


def nombres(texte: str) -> set[str]:
    return {_normaliser_nombre(m) for m in _MOTIF_NOMBRE.findall(texte)}


def verifier(reponse: str, notes_lues: dict[str, str], observations: list[str],
            question: str = "", exiger_citation: bool = True) -> Verification:
    """notes_lues : {nom: contenu} des notes lues ; observations : résultats bruts des outils ;
    question : les nombres donnés par l'utilisateur (ex. « 20 % ») sont légitimes."""
    v = Verification(citations=citations(reponse))
    if exiger_citation and not v.citations:
        v.problemes.append("aucune source citée")
    for nom in v.citations:
        if nom not in notes_lues:
            v.problemes.append(f"source citée mais non lue pendant l'exécution : {nom}")
    sans_citations = MOTIF_CITATION.sub("", reponse)
    textes_appui = [
            notes_lues.get(n, "") for n in v.citations
    ] + observations + [question]
    appui = nombres(" ".join(textes_appui))
    for n in sorted(nombres(sans_citations)):
        if len(n.split(".")[0]) >= 2 and n not in appui: #exclure faux negatif et si un nbre pas dans la liste des nbres suivies par l'agent alors
            v.problemes.append(f"nombre non étayé : {n}")
    return v