from __future__ import annotations

from abc import ABC, abstractmethod

from titanic.app.dtos.crew_walter_roaster_dto import WalterQuery, WalterResponse


class WalterPort(ABC):
    """Walter 소개 출력 포트 (ABC)."""

    @abstractmethod
    async def get_train_set(self):
        ''' survived 컬럼이 있는 데이터 전체를 데이터프레임으로 반환하는 메소드'''
        pass

    @abstractmethod
    async def get_test_set(self):
        ''' survived 컬럼이 없는 데이터 전체를 데이터프레임으로 반환하는 메소드 '''
        pass

    @abstractmethod
    def introduce_myself(self, query: WalterQuery)->WalterResponse:
        pass
