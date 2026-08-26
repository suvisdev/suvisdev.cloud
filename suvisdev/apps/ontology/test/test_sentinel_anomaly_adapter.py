import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

from ontology.app.dtos.anomaly_detection_dto import AnomalyResult  # noqa: E402

# ── 실제 GPU(또는 CPU 폴백) + CLIP 다운로드가 필요한 통합 테스트 ────────
# apps/ontology/resources/sentinel_poster/test/{good,blur}에서 각각 정상
# 포스터·합성 블러 샘플을 하나씩 골라 두 신호(포스터 여부/블러 여부)를 검증한다.


@pytest.mark.gpu
def test_detect_returns_anomaly_result_via_port_for_good_poster() -> None:
    from ontology.adapter.outbound.resource_adapters.sentinel_anomaly.sentinel_anomaly_adapter import (
        SentinelAnomalyAdapter,
    )
    from ontology.app.use_cases.anomaly_detection_interactor import AnomalyDetectionInteractor

    image_path = (
        ROOT / "apps" / "ontology" / "resources" / "sentinel_poster" / "test" / "good" / "0000.jpg"
    )
    port = SentinelAnomalyAdapter()
    use_case = AnomalyDetectionInteractor(detector_port=port)

    result = use_case.detect(image_path.read_bytes())

    assert isinstance(result, AnomalyResult)
    assert 0.0 <= result.poster_confidence <= 1.0
    assert result.is_poster is True
    assert result.is_blurry is False


@pytest.mark.gpu
def test_detect_flags_synthetic_blur_sample() -> None:
    from ontology.adapter.outbound.resource_adapters.sentinel_anomaly.sentinel_anomaly_adapter import (
        SentinelAnomalyAdapter,
    )
    from ontology.app.use_cases.anomaly_detection_interactor import AnomalyDetectionInteractor

    image_path = (
        ROOT / "apps" / "ontology" / "resources" / "sentinel_poster" / "test" / "blur" / "0000.jpg"
    )
    port = SentinelAnomalyAdapter()
    use_case = AnomalyDetectionInteractor(detector_port=port)

    result = use_case.detect(image_path.read_bytes())

    assert isinstance(result, AnomalyResult)
    assert result.is_blurry is True


if __name__ == "__main__":
    print(test_detect_returns_anomaly_result_via_port_for_good_poster())
