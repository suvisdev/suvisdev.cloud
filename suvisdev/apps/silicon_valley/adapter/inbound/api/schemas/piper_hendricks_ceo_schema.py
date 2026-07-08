from pydantic import BaseModel, Field


class HendricksCeoSchema(BaseModel):

    id: int = Field(0, description="Piper ID")
    name: str = Field("리처드 헨드릭스", description="Character's name")
    # 파이드 파이퍼 CEO. 중간 아웃 압축 알고리즘을 개발한 기술 창업자

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Richard Hendricks",
            }
        }
    }
