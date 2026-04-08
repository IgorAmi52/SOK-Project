from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SearchQuery:
    """Encapsulates a user-supplied text search query."""

    text: str

    def normalized(self) -> str:
        """Return the query text stripped of whitespace and lowercased."""
        return self.text.strip().lower()
