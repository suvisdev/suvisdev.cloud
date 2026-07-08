from pydantic import BaseModel, Field


class BighettiHrSchema(BaseModel):

    id: int = Field(0, description="Piper ID")
    name: str = Field("넬슨 빅헤티", description="Character's name")
    # 파이드 파이퍼 공동창업자 중 한 명. 기술보다 운이 따르는 인물로 후리에서도 승진함

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 5,
                "name": "Nelson Bighetti",
            }
        }
    }
