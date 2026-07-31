import uuid

import pytest

from analytics.app.use_cases.record_visit_interactor import RecordVisitInteractor
from analytics.tests.app.fakes import _FakeVisitorActivityRepository


class TestRecordVisit:
    @pytest.mark.asyncio
    async def test_valid_visitor_id_is_recorded(self):
        repository = _FakeVisitorActivityRepository()
        interactor = RecordVisitInteractor(repository=repository)
        visitor_id = str(uuid.uuid4())

        await interactor.record(visitor_id)

        assert await repository.count_unique_total() == 1

    @pytest.mark.asyncio
    async def test_invalid_visitor_id_is_ignored(self):
        repository = _FakeVisitorActivityRepository()
        interactor = RecordVisitInteractor(repository=repository)

        await interactor.record("<script>alert(1)</script>")

        assert await repository.count_unique_total() == 0

    @pytest.mark.asyncio
    async def test_same_visitor_twice_stays_one_unique(self):
        repository = _FakeVisitorActivityRepository()
        interactor = RecordVisitInteractor(repository=repository)
        visitor_id = str(uuid.uuid4())

        await interactor.record(visitor_id)
        await interactor.record(visitor_id)

        assert await repository.count_unique_total() == 1
