from __future__ import annotations

from abc import ABC, abstractmethod

from dispatch.adapter.inbound.api.schemas.adress_schema import AdressIntroduceSchema
from dispatch.app.dtos.adress_dto import AdressIntroduceResponse, AdressResponse, AdressSearchResult


class AdressUseCase(ABC):
    @abstractmethod
    async def receive_uploaded_records(self, csv_text: str) -> AdressResponse: ...

    @abstractmethod
    async def introduce_myself(self, schema: AdressIntroduceSchema) -> AdressIntroduceResponse: ...

    @abstractmethod
    async def search(self, q: str) -> list[AdressSearchResult]: ...
