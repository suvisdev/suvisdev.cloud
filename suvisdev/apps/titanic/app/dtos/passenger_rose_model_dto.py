from dataclasses import dataclass


@dataclass(frozen=True) # 생성 후 수정 불가하도록 설정
class RoseModelQuery:

    id: int   # 직관적인 타입 변경
    name: str


@dataclass(frozen=True) # 생성 후 수정 불가하도록 설정
class RoseModelResponse:

    id: int   # 직관적인 타입 변경
    name: str


@dataclass(frozen=True)
class RoseModelFeatureRow:
    """James/Walter가 적재한 승객 1명의 학습용 원본 피처 (DB 원본은 모두 str)."""

    pclass: str
    sex: str
    age: str
    sib_sp: str
    parch: str
    fare: str
    embarked: str
    survived: str


@dataclass(frozen=True)
class RoseModelTrainCommand:
    strategy: str


@dataclass(frozen=True)
class RoseModelTrainResponse:
    strategy: str
    n_samples: int
    accuracy: float


@dataclass(frozen=True)
class RoseModelPredictCommand:
    strategy: str
    pclass: str
    sex: str
    age: str
    sib_sp: str
    parch: str
    fare: str
    embarked: str


@dataclass(frozen=True)
class RoseModelPredictResponse:
    strategy: str
    survived: bool
    probability: float
