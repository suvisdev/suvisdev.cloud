from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from titanic.adapter.inbound.api.schemas.crew_walter_roaster_schema import WalterSchema
from titanic.app.dtos.crew_walter_roaster_dto import WalterResponse


class WalterUseCase(ABC):
    """roaster input port."""

    @abstractmethod
    async def get_train_set(self) -> pd.DataFrame:
        '''월터가 DB에서 train set만 가져오는 메소드'''
        pass

    @abstractmethod
    async def get_test_set(self) -> pd.DataFrame:
        '''월터가 DB에서 test set만 가져오는 메소드'''
        pass

    @abstractmethod
    async def introduce_myself(self, schema: WalterSchema) -> WalterResponse:
        pass
