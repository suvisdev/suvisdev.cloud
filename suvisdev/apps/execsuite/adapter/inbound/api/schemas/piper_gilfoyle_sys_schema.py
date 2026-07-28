from pydantic import BaseModel, Field


class GilfoyleSysSchema(BaseModel):

    id: int = Field(0, description="Piper ID")
    name: str = Field("버트람 길포일", description="Character's name")
    # 파이드 파이퍼 시스템 아키텍처 담당. 사탄주의자이자 뛰어난 인프라·보안 전문가

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 2,
                "name": "Bertram Gilfoyle",
            }
        }
    }
