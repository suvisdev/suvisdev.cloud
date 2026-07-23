"""06(Sentinel) H3 Phase A — PatchCore 파이프라인 정합성 검증(MVTec AD bottle).

포스터 도메인(Phase B) 데이터로 넘어가기 전, PatchCore 구현 자체가 논문 수치를
재현하는지 공개 벤치마크(MVTec AD)로 먼저 확인한다. 종횡비 처리·정상 분포
다양성 문제는 Phase B에서 별도로 다룬다(여기서는 파이프라인 정합성만 검증).

목표: bottle 카테고리 image-level AUROC — PatchCore 논문 보고치 100.0%.

Usage (컨테이너 안에서):
  python scripts/verify_patchcore_mvtec_sanity.py
"""

from __future__ import annotations

from anomalib.data import MVTecAD
from anomalib.engine import Engine
from anomalib.models import Patchcore


def main() -> None:
    # num_workers=0: 컨테이너 기본 /dev/shm이 64MB뿐이라 멀티프로세스 DataLoader의
    # 프로세스 간 텐서 공유(shared memory)가 바로 고갈된다. 단일 프로세스로 우회.
    datamodule = MVTecAD(root="/tmp/mvtec_ad", category="bottle", num_workers=0)
    model = Patchcore()
    engine = Engine(default_root_dir="/tmp/patchcore_mvtec_results")

    engine.fit(model=model, datamodule=datamodule)
    results = engine.test(model=model, datamodule=datamodule)

    print("RESULTS:", results)


if __name__ == "__main__":
    main()
