from pydantic import BaseModel, Field


class PlatformUsersSchema(BaseModel):

    id: int = Field(0, description="Users ID")
    name: str = Field("관객 (Audience)", description="Audience's name")
    # 서비스를 이용하는 일반 사용자이자 모든 Mova 데이터의 실질적 주체. users 테이블 관련
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "관객 (Audience)",
            }
        }
    }
