from typing import Literal

from pydantic import BaseModel, Field


class RoseModelSchema(BaseModel):

    id: int = Field(0, description="Passenger ID")
    name: str = Field("로즈 드윗 부카터", description="Passenger's name")
    # 타이타닉의 실질적 모델이자 주인공. 104세의 생존자로 비아트리스 우드를 모티브 삼아 자유를 갈망한 인물

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 10,
                "name": "Rose DeWitt Bukater",
            }
        }
    }


RoseModelStrategyKey = Literal[
    "xgboost",
    "random_forest",
    "lightgbm",
    "catboost",
    "logistic_regression",
    "decision_tree",
    "svm",
    "knn",
    "naive_bayes",
    "kmeans_pca",
]


class RoseModelTrainSchema(BaseModel):
    """titanic-algorithm.md TOP 10 전략 중 하나를 골라 DB 적재 데이터로 학습."""

    strategy: RoseModelStrategyKey = Field(..., description="사용할 알고리즘 전략 키")


class RoseModelPredictSchema(RoseModelTrainSchema):
    """전략을 학습시킨 뒤 한 승객의 생존 여부를 예측."""

    pclass: str = Field("3", description="객실 등급 1/2/3")
    sex: str = Field("male", description="성별 male/female")
    age: str = Field("", description="나이")
    sib_sp: str = Field("0", description="형제자매·배우자 수")
    parch: str = Field("0", description="부모·자녀 수")
    fare: str = Field("", description="요금")
    embarked: str = Field("S", description="승선 항구 C/Q/S")
