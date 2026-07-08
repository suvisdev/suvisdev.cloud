from pydantic import BaseModel, Field


class PlatformAdminsSchema(BaseModel):

    id: int = Field(0, description="Admins ID")
    name: str = Field("총지배인 (Executive)", description="Executive's name")
    # 극장 전체를 관리하는 최고 책임자. admins 테이블 관련
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "총지배인 (Executive)",
            }
        }
    }
