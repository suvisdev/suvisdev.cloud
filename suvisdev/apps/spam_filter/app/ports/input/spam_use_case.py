from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from spam_filter.app.dtos.spam_dto import SpamClassifyDto


class SpamClassifyUseCase(Protocol):
    def classify(self, *, subject: str, body: str, sender: str | None) -> SpamClassifyDto: ...
