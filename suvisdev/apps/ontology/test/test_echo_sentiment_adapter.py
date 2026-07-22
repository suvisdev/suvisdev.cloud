import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.app.dtos.sentiment_analysis_dto import SentimentResult  # noqa: E402


# ── 실제 GPU + 학습된 어댑터가 필요한 통합 테스트 ─────────────────────
# H3(파인튜닝)에서 저장한 apps/ontology/runs/echo_sentiment/adapter가 있어야
# 통과한다. 실행 전 lora-server 등 다른 GPU 프로세스를 내려 VRAM을 확보할 것.

@pytest.mark.gpu
def test_echo_analyze_returns_sentiment_result_via_port() -> None:
    from ontology.adapter.outbound.resource_adapters.echo_sentiment.echo_sentiment_adapter import (
        EchoSentimentAdapter,
    )
    from ontology.app.use_cases.sentiment_analysis_interactor import SentimentAnalysisInteractor

    adapter_dir = ROOT / "apps" / "ontology" / "runs" / "echo_sentiment" / "adapter"
    port = EchoSentimentAdapter(adapter_dir=adapter_dir)
    use_case = SentimentAnalysisInteractor(sentiment_port=port)

    result = use_case.analyze("연기도 좋고 스토리도 탄탄했다")

    assert isinstance(result, SentimentResult)
    assert result.label in ("긍정", "부정")
    assert 0.0 <= result.score <= 1.0
    assert result.label == "긍정"


if __name__ == "__main__":
    print(test_echo_analyze_returns_sentiment_result_via_port())
