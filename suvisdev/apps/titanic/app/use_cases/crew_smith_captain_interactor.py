from __future__ import annotations

import asyncio
import logging

from pandas import DataFrame

from titanic.adapter.inbound.api.schemas.crew_smith_captain_schema import (
    ChatSchema,
    SmithCaptainSchema,
)
from titanic.app.dtos.crew_smith_captain_dto import (
    SmithCaptainQuery,
    SmithCaptainResponse,
    SmithChatResponse,
)
from titanic.app.ports.input.crew_andrews_architect_use_case import AndrewsArchitectUseCase
from titanic.app.ports.input.crew_hartley_violin_use_case import HartleyViolinUseCase
from titanic.app.ports.input.crew_lowe_boat_use_case import LoweBoatUseCase
from titanic.app.ports.input.crew_smith_captain_use_case import SmithCaptainUseCase
from titanic.app.ports.input.crew_walter_roaster_use_case import WalterUseCase
from titanic.app.ports.input.passenger_cal_tester_use_case import CalTesterUseCase
from titanic.app.ports.input.passenger_jack_trainer_use_case import JackTrainerUseCase
from titanic.app.ports.input.passenger_rose_model_use_case import RoseModelUseCase
from titanic.app.ports.output.crew_smith_captain_port import SmithCaptainPort

logger = logging.getLogger(__name__)


class SmithCaptainInteractor(SmithCaptainUseCase):
    def __init__(self, repository: SmithCaptainPort,
                 andrews: AndrewsArchitectUseCase,
                 jack: JackTrainerUseCase,
                 cal: CalTesterUseCase,
                 walter: WalterUseCase,
                 rose: RoseModelUseCase,
                 lowe: LoweBoatUseCase,
                 hartley: HartleyViolinUseCase):
        self._repository = repository
        self.andrews = andrews
        self.jack = jack
        self.cal = cal
        self.walter = walter
        self.rose = rose
        self.lowe = lowe
        self.hartley = hartley

    async def chat(self, schema: ChatSchema) -> SmithChatResponse:
        last_user_msg = next(
            (m.content for m in reversed(schema.messages) if m.role == "user"), ""
        )
        logger.info(f"[SmithCaptainInteractor] chat | q={last_user_msg!r}")

        train_set: DataFrame = await self.walter.get_train_set()
        test_set: DataFrame  = await self.walter.get_test_set()
        train_result: dict   = await self.jack.train_model(train_set, test_set)
        test_result          = await self.cal.test_model(test_set, train_result)

        ml_context = {
            "predictions":        test_result.predictions,
            "test_meta":          train_result.get("test_meta"),
            "train_set":          train_set,
            "best_model":         test_result.best.strategy,
            "accuracy":           test_result.best.accuracy,
            "n_train":            train_result.get("train_samples", 0),
            "trained_models":     train_result.get("trained_models", []),
            "trained_strategies": train_result.get("trained_strategies", {}),
        }

        reply = await asyncio.to_thread(self.andrews.generate_reply, last_user_msg, ml_context)

        logger.info(f"[SmithCaptainInteractor] chat 완료 | best={ml_context['best_model']} reply={reply[:60]!r}")
        return SmithChatResponse(reply=reply)
    
    
    
    async def introduce_myself(self, schemas: SmithCaptainSchema) -> SmithCaptainResponse:
        return await self._repository.introduce_myself(SmithCaptainQuery(
            id=schemas.id,
            name=schemas.name,
        ))


