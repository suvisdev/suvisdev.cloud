import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))  # tests/ (스크립트 직접 실행 시 korean_ai 임포트)

from korean_ai import run_korean_ai

# ── 일반 테스트 (ollama mock, 서버 불필요) ────────────────────────────

class TestRunKoreanAi:
    def test_returns_llm_response_content(self):
        with patch("korean_ai.ollama.chat") as mock_chat:
            mock_chat.return_value = {"message": {"content": "AI 답변입니다."}}
            result = run_korean_ai("안녕하세요")
        assert result == "AI 답변입니다."

    def test_calls_ollama_with_correct_model(self):
        with patch("korean_ai.ollama.chat") as mock_chat:
            mock_chat.return_value = {"message": {"content": "응답"}}
            run_korean_ai("테스트 문장")
        assert mock_chat.call_args.kwargs["model"] == "anpigon/eeve-korean-10.8b:latest"

    def test_message_role_is_user(self):
        with patch("korean_ai.ollama.chat") as mock_chat:
            mock_chat.return_value = {"message": {"content": "응답"}}
            run_korean_ai("테스트")
        messages = mock_chat.call_args.kwargs["messages"]
        assert messages[0]["role"] == "user"


# ── ollama 통합 테스트 (실제 서버 필요) ─────────────────────────────

@pytest.mark.ollama
def test_real_ollama_korean_question():
    result = run_korean_ai("타이타닉의 생존자 수는 몇 명인가요?")
    print("\n--- AI 최종 답변 ---")
    print(result)
    assert isinstance(result, str)


# ── 스크립트 직접 실행 ────────────────────────────────────────────────

if __name__ == "__main__":
    question = "타이타닉의 생존자 수는 몇 명인가요?"
    print(f"질문: {question}")
    answer = run_korean_ai(question)
    print("\n--- AI 최종 답변 ---")
    print(answer)
