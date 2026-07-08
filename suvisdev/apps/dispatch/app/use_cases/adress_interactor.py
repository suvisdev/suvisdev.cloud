from __future__ import annotations

import csv
from io import StringIO

from dispatch.adapter.inbound.api.schemas.adress_schema import (
    AdressIntroduceSchema,
    AdressRowSchema,
)
from dispatch.app.dtos.adress_dto import (
    AdressCommand,
    AdressIntroduceQuery,
    AdressIntroduceResponse,
    AdressResponse,
    AdressSearchQuery,
    AdressSearchResult,
)
from dispatch.app.ports.input.adress_use_case import AdressUseCase
from dispatch.app.ports.output.adress_port import AdressPort


class AdressInteractor(AdressUseCase):
    def __init__(self, *, repository: AdressPort) -> None:
        self._repository = repository

    def _parse_csv(self, text: str) -> list[AdressRowSchema]:
        if not text.strip():
            raise ValueError("빈 CSV 파일입니다.")
        reader = csv.DictReader(StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("CSV 헤더를 읽을 수 없습니다.")
        rows: list[AdressRowSchema] = []
        for raw_row in reader:
            row = {k: (v or "") for k, v in raw_row.items() if k is not None}
            schema = AdressRowSchema.model_validate(row, from_attributes=False)
            if not schema.email.strip():
                continue
            rows.append(schema)
        if not rows:
            raise ValueError("이메일이 있는 주소록 행이 없습니다.")
        return rows

    async def receive_uploaded_records(self, csv_text: str) -> AdressResponse:
        schemas = self._parse_csv(csv_text)
        commands = [
            AdressCommand(
                first_name=s.first_name,
                middle_name=s.middle_name,
                last_name=s.last_name,
                phonetic_first_name=s.phonetic_first_name,
                phonetic_middle_name=s.phonetic_middle_name,
                phonetic_last_name=s.phonetic_last_name,
                name_prefix=s.name_prefix,
                name_suffix=s.name_suffix,
                nickname=s.nickname,
                file_as=s.file_as,
                organization_name=s.organization_name,
                organization_title=s.organization_title,
                organization_department=s.organization_department,
                birthday=s.birthday,
                notes=s.notes,
                photo=s.photo,
                labels=s.labels,
                email_label=s.email_label,
                email=s.email,
            )
            for s in schemas
        ]
        saved = await self._repository.bulk_save(commands)
        return AdressResponse(row_count=saved)

    async def introduce_myself(self, schema: AdressIntroduceSchema) -> AdressIntroduceResponse:
        return await self._repository.introduce_myself(
            AdressIntroduceQuery(id=schema.id, name=schema.name)
        )

    async def search(self, q: str) -> list[AdressSearchResult]:
        return await self._repository.search(AdressSearchQuery(q=q))
