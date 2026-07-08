from pydantic import BaseModel, Field


class DunnCooSchema(BaseModel):

    id: int = Field(0, description="Piper ID")
    name: str = Field("도널드 던", description="Character's name")
    # 파이드 파이퍼 COO. 이전 후리 직원으로 리처드의 충직한 운영 담당자

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 4,
                "name": "Donald Dunn",
            }
        }
    }
