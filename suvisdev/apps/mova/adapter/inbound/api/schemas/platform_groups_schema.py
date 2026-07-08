
from pydantic import BaseModel, Field


class PlatformGroupsSchema(BaseModel):

    id: int = Field(0, description="Groups ID")
    name: str = Field("길드 (Guild)", description="Guild's name")
    # 극장 조직의 직책 체계를 정의하는 규약. groups 테이블 관련
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "길드 (Guild)",
            }
        }
    }
