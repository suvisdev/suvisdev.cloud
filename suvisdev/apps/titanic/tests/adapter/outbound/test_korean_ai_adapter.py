from unittest.mock import patch

from titanic.adapter.outbound.llm.korean_ai_adapter import run_korean_ai


def _mock_ollama_response(content: str) -> dict:
    return {"message": {"content": content}}


class TestRunKoreanAi:
    def test_returns_llm_response_content(self):
        with patch("titanic.adapter.outbound.llm.korean_ai_adapter.ollama.chat") as mock_chat:
            mock_chat.return_value = _mock_ollama_response("AI 답변입니다.")

            result = run_korean_ai("안녕하세요")

        assert result == "AI 답변입니다."

    def test_calls_ollama_with_correct_model(self):
        with patch("titanic.adapter.outbound.llm.korean_ai_adapter.ollama.chat") as mock_chat:
            mock_chat.return_value = _mock_ollama_response("응답")

            run_korean_ai("테스트 문장")

        call_kwargs = mock_chat.call_args
        assert call_kwargs.kwargs["model"] == "anpigon/eeve-korean-10.8b:latest"

    def test_calls_ollama_with_user_role(self):
        with patch("titanic.adapter.outbound.llm.korean_ai_adapter.ollama.chat") as mock_chat:
            mock_chat.return_value = _mock_ollama_response("응답")

            run_korean_ai("테스트 문장")

        messages = mock_chat.call_args.kwargs["messages"]
        assert messages[0]["role"] == "user"

    def test_kiwi_preprocessed_text_is_sent_to_llm(self):
        """Kiwi로 전처리된 문자열(비어있지 않은 string)이 ollama에 전달된다."""
        with patch("titanic.adapter.outbound.llm.korean_ai_adapter.ollama.chat") as mock_chat:
            mock_chat.return_value = _mock_ollama_response("응답")

            run_korean_ai("안녕하세요")

        content_sent = mock_chat.call_args.kwargs["messages"][0]["content"]
        assert isinstance(content_sent, str)
        assert len(content_sent) > 0
        # ollama는 정확히 1번만 호출돼야 한다
        assert mock_chat.call_count == 1

    def test_noun_extraction_from_korean_text(self):
        """명사 추출 로직이 실제 Kiwi로 동작하는지 확인한다 (ollama만 mock)."""
        with patch("titanic.adapter.outbound.llm.korean_ai_adapter.ollama.chat") as mock_chat:
            mock_chat.return_value = _mock_ollama_response("응답")

            # 예외 없이 실행되어야 하며, 결과를 반환해야 한다
            result = run_korean_ai("올라마와 키위파이의 차이점을 알려줘")

        assert isinstance(result, str)
