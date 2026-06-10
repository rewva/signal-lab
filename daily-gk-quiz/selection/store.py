from __future__ import annotations

import json
from pathlib import Path

from selection.models import Question, HistoryRecord

class Store:
    def __init__(self, history_path, bank_path):
        self._history_path = Path(history_path)
        self._bank_path = Path(bank_path)

    def load_history(self) -> list[HistoryRecord]:
        return [HistoryRecord.from_dict(d) for d in self._read(self._history_path)]

    def load_bank(self) -> list[Question]:
        return [Question.from_dict(d) for d in self._read(self._bank_path)]

    def save_bank(self, questions: list[Question]) -> None:
        self._write(self._bank_path, [q.to_dict() for q in questions])

    def append_history(self, record: HistoryRecord) -> None:
        rows = self._read(self._history_path)
        rows.append(record.to_dict())
        self._write(self._history_path, rows)

    def _read(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)
