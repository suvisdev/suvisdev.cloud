from pydantic import BaseModel, Field


class DineshDashSchema(BaseModel):

    id: int = Field(0, description="Piper ID")
    name: str = Field("디네시 추그타이", description="Character's name")
    # 파이드 파이퍼 대시보드 개발자. 파키스탄 출신으로 길포일과 끊임없이 경쟁함

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 3,
                "name": "Dinesh Chugtai",
            }
        }
    }
