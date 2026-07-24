import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
APPS = ROOT / "apps"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

# api 애그리게이터(__init__)를 먼저 완전 로드해 import 순서를 고정한다 — vision_use_case가
# adapter 계층 vision_schema를 임포트하며 생기는 기존 잠재 순환(app→adapter)을 회피.
# (근본 원인은 별도 백로그, WORK_LOG.md 2026-07-24 참고.)
import ontology.adapter.inbound.api  # noqa: E402,F401

from ontology.app.dtos.vision_dto import (  # noqa: E402
    VisionImageCommand,
    VisionIntroduceQuery,
    VisionIntroduceResponse,
    VisionUploadResponse,
)
from ontology.app.ports.output.vision_port import VisionPort  # noqa: E402

_SENTINEL_ROOT = ROOT / "apps" / "ontology" / "resources" / "sentinel_poster" / "test"


class _FakeVisionRepository(VisionPort):
    """저장 백엔드(S3/DB)와 무관하게 게이트 로직만 검증하기 위한 fake.

    save_image가 호출됐는지(=게이트를 통과했는지)를 기록한다.
    """

    def __init__(self) -> None:
        self.saved: list[VisionImageCommand] = []

    async def introduce_myself(self, query: VisionIntroduceQuery) -> VisionIntroduceResponse:
        return VisionIntroduceResponse(id=query.id, name=query.name)

    async def save_image(self, command: VisionImageCommand) -> VisionUploadResponse:
        self.saved.append(command)
        return VisionUploadResponse(
            filename=command.filename,
            size_bytes=len(command.content),
            saved_path=f"fake://{command.filename}",
        )


def _make_interactor(repo: _FakeVisionRepository):
    from ontology.adapter.outbound.resource_adapters.sentinel_anomaly.sentinel_anomaly_adapter import (
        SentinelAnomalyAdapter,
    )
    from ontology.app.use_cases.vision_interactor import VisionInteractor

    return VisionInteractor(repository=repo, anomaly_port=SentinelAnomalyAdapter())


# ── 실제 GPU(또는 CPU 폴백) + CLIP 다운로드가 필요한 통합 테스트 ────────


@pytest.mark.gpu
@pytest.mark.asyncio
async def test_good_poster_passes_gate_and_saves() -> None:
    repo = _FakeVisionRepository()
    interactor = _make_interactor(repo)

    image = (_SENTINEL_ROOT / "good" / "0000.jpg").read_bytes()
    response = await interactor.upload_image("good.jpg", image)

    assert isinstance(response, VisionUploadResponse)
    assert len(repo.saved) == 1  # 저장까지 통과
    assert response.is_poster_warning is False
    assert response.sharpness_score >= 345.77


@pytest.mark.gpu
@pytest.mark.asyncio
async def test_blurry_image_hard_rejected_and_not_saved() -> None:
    repo = _FakeVisionRepository()
    interactor = _make_interactor(repo)

    image = (_SENTINEL_ROOT / "blur" / "0000.jpg").read_bytes()
    with pytest.raises(ValueError, match="흐릿"):
        await interactor.upload_image("blur.jpg", image)

    assert repo.saved == []  # 하드 게이트 — 저장 안 됨


@pytest.mark.gpu
@pytest.mark.asyncio
async def test_non_poster_soft_flagged_but_saved() -> None:
    repo = _FakeVisionRepository()
    interactor = _make_interactor(repo)

    # cast 프로필 사진 — 확실한 비포스터(conf≈0.003)지만 블러 게이트는 통과(sharp≈497).
    image = (_SENTINEL_ROOT / "non_poster_easy" / "cast_0001.jpg").read_bytes()
    response = await interactor.upload_image("nonposter.jpg", image)

    # 소프트 — 차단하지 않고 저장하되 경고 플래그를 세운다
    assert len(repo.saved) == 1
    assert response.is_poster_warning is True
