from dataclasses import dataclass, field


@dataclass(frozen=True) # 생성 후 수정 불가하도록 설정
class CalTesterQuery:

    id: int   # 직관적인 타입 변경
    name: str

@dataclass(frozen=True) # 생성 후 수정 불가하도록 설정
class CalTesterResponse:

    id: int   # 직관적인 타입 변경
    name: str


@dataclass(frozen=True)
class KaggleScoreEntry:
    """전략 1개의 캐글 채점 결과."""

    strategy: str
    n_samples: int
    accuracy: float


@dataclass(frozen=True)
class TestmodelResponse:
    """titanic-algorithm.md TOP 10 전략 전체 채점 결과 — 최고점 전략 + 전체 순위 + 예측값."""

    best: KaggleScoreEntry
    leaderboard: list[KaggleScoreEntry]
    predictions: list[float] = field(default_factory=list)