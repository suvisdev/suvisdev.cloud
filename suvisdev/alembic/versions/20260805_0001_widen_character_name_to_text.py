"""widen characters.character_name from VARCHAR(50) to TEXT

VARCHAR(50)이 실측 데이터를 못 담아 배치 중 StringDataRightTruncation을
유발한 문제 수정(_docs/WORK_LOG.md 2026-08-05 조사 참고).

근거:
1. TMDB `credits.cast[].character` 필드를 EC2 실 배치(1000편)와 대조한 결과
   실측 최댓값 332자(The Simpsons Movie — 애니메이션 다역 성우 캐릭터명이
   " / "로 이어짐), 그 외에도 84자(Split, 1인 다역), 59자(생애주기·자막
   병기 표기) 등 50자를 넘는 합법적 TMDB 데이터가 다수 확인됨 — 데이터
   이상이 아니라 컬럼 길이 자체가 처음부터 너무 작았다.
2. 애니메이션 다역 성우·1인 다역 배우는 캐스팅 관례상 구조적으로 상한이
   없다 — 임의의 VARCHAR(n)을 잡아도 n을 넘는 사례가 또 나올 수 있다.
3. PostgreSQL은 VARCHAR(n)과 TEXT의 저장·성능이 동일하다(길이 제약만
   추가 CHECK로 처리되는 차이). `movies.poster_url`도 이미 TEXT를 쓰고
   있어 이 저장소 관례에도 맞는다.
4. `character_name`은 인덱스 대상이 아니다(`(movie_id, actor_id,
   character_name)` UNIQUE는 있지만 조회 인덱스로 쓰이진 않음) — TEXT로
   바꿔도 인덱스 크기·성능에 영향 없다.

downgrade는 의도적으로 미지원 — TEXT로 넓힌 뒤 저장된 50자 초과 데이터를
truncate 없이 VARCHAR(50)으로 되돌릴 방법이 없고(자르면 데이터 손실,
UNIQUE 제약 충돌 가능성도 새로 생김), 이 리비전의 존재 이유 자체가 "50자
제한이 틀렸다"는 것이므로 되돌리는 것 자체가 무의미하다. 호출 시 명시적
에러로 안내한다.

Revision ID: 20260805_0001
Revises: 20260731_0001
Create Date: 2026-08-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0001"
down_revision: str | None = "20260731_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "characters",
        "character_name",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    raise RuntimeError(
        "20260805_0001 downgrade 미지원 — TEXT로 넓힌 뒤 저장된 50자 초과 "
        "character_name을 VARCHAR(50)으로 되돌리려면 truncate(데이터 손실)가 "
        "필요하다. 원복이 필요하면 백업에서 복원하거나 truncate 방식을 "
        "직접 결정해 별도 리비전으로 작성할 것."
    )
