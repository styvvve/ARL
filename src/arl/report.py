from __future__ import annotations

import json
from pathlib import Path

class Report:
    def __init__(self, path: Path | None, file: str = "traces.jsonl"):
        self.path = Path(path) / file if path else None

    def write(self, records: dict) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(records, ensure_ascii=False, default=str) + "\n")