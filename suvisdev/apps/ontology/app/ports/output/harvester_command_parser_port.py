from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.app.dtos.harvester_command_dto import HarvesterCommand


class HarvesterCommandParserPort(ABC):
    @abstractmethod
    async def parse(self, command_text: str) -> HarvesterCommand:
        """자연어 명령에서 검색 키워드와 개수(limit)를 추출한다."""
