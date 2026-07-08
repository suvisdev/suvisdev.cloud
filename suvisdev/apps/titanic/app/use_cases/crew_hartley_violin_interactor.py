from __future__ import annotations

import io
import logging

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from titanic.adapter.inbound.api.schemas.crew_hartley_violin_schema import HartleyViolinSchema
from titanic.app.dtos.crew_hartley_violin_dto import HartleyViolinQuery, HartleyViolinResponse
from titanic.app.ports.input.crew_hartley_violin_use_case import HartleyViolinUseCase
from titanic.app.ports.output.crew_hartley_violin_port import HartleyViolinPort

matplotlib.use("Agg")  # GUI 없는 환경에서 렌더링

logger = logging.getLogger(__name__)


class HartleyViolinInteractor(HartleyViolinUseCase):
    def __init__(self, repository: HartleyViolinPort) -> None:
        self._repository = repository

    def get_correlation_image(self, df: pd.DataFrame) -> bytes:
        numeric_df = df.select_dtypes(include="number")
        corr = numeric_df.corr()

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            corr,
            annot=True,
            cmap="coolwarm",
            fmt=".2f",
            linewidths=0.5,
            ax=ax,
        )
        ax.set_title("Titanic Feature Correlation")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        plt.close(fig)

        logger.info(f"[HartleyViolinInteractor] 상관관계 히트맵 생성 | features={list(numeric_df.columns)}")
        return buf.read()

    async def introduce_myself(self, schemas: HartleyViolinSchema) -> HartleyViolinResponse:
        return await self._repository.introduce_myself(HartleyViolinQuery(
            id=schemas.id,
            name=schemas.name,
        ))
