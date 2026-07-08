from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class JamesSchema(BaseModel):
    """James CSV 업로드 한 행 — CSV 헤더 `Sex`는 필드명 `gender`로 매핑."""

    model_config = ConfigDict(populate_by_name=True)

    passenger_id: str = Field(default="", alias="PassengerId")
    survived: str = Field(default="", alias="Survived")
    pclass: str = Field(default="", alias="Pclass")
    name: str = Field(default="", alias="Name")
    gender: str = Field(default="", alias="Sex")
    age: str = Field(default="", alias="Age")
    sib_sp: str = Field(default="", alias="SibSp")
    parch: str = Field(default="", alias="Parch")
    ticket: str = Field(default="", alias="Ticket")
    fare: str = Field(default="", alias="Fare")
    cabin: str = Field(default="", alias="Cabin")
    embarked: str = Field(default="", alias="Embarked")

class JamesUploadResponse(BaseModel):
    row_count: int = 0
    rows: list[JamesSchema] = Field(default_factory=list)


class JamesIntroduceSchema(BaseModel):
    id: int = Field(0, description="Director ID")
    name: str = Field("제임스 카메론", description="Director name")

