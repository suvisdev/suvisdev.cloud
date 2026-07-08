from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class ChatSchema(BaseModel):
    messages: list[ChatMessageSchema] = Field(..., description="채팅 메시지 히스토리")
    model: str | None = None
    systemInstruction: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "messages": [{"role": "user", "content": "탑승객이 몇 명이야 ?"}],
            }
        }
    }
class SmithCaptainSchema(BaseModel):

    id: int = Field(0, description="Captain ID")
    name: str = Field("에드워드 스미스", description="Captain's name")
    # 타이타닉 선장. 백만장자들의 선장이라 불렸으며 고조되는 위기 속에 배와 운명을 함께함

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 4,
                "name": "Edward Smith",
            }
        }
    }



    