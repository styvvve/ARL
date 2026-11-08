"""seul composante qui touche aux notes"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

MAX_SIZE = 20000


def _flatten(text: str) -> str:
    """Normalise le texte pour pouvoir le comparer avec les notes"""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


class NotesRepository:
    def __init__(self, directory: Path):
        self.directory = Path(directory).resolve()

    def list(self) -> list[str]:
        return sorted(p.name for p in self.directory.glob("*.md"))

    def path(self, name: str) -> Path | None:
        """Chemin de la note SSI elle est dans le dossier ; sinon None"""
        if "/" in name or "\\" in name or not name.endswith(".md"):
            return None
        path = (self.directory / name).resolve() #absolu
        return path if path.parent == self.directory and path.is_file() else None

    def read(self, name: str) -> str | None:
        path = self.path(name)
        return path.read_text(encoding="utf-8")[:MAX_SIZE] if path else None

    def search(self, query: str, limit: int = 5) -> list[tuple[str, int, str]]:
        """seach with keyword matching without case sensitivity"""
        words = re.findall(r"\w{3,}", _flatten(query))[:8]
        results = []
        for path in self.directory.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            flat = _flatten(text)
            score = sum(flat.count(w) for w in words) + 3 * sum(w in _flatten(path.name) for w in words)
            if score:
                pos = min((flat.find(word) for word in words if word in flat), default=0)
                results.append((path.name, score, " ".join(text[max(0, pos - 60): pos + 140].split())))
        results.sort(key=lambda x: (-x[1], x[0]))
        return results[:limit]