from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SearchQuery:
    text: str

    def normalized(self) -> str:
        return self.text.strip().lower()
