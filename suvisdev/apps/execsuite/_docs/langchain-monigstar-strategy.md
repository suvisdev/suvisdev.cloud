# LangChain 활용 사례 — Morningstar: 맞춤형 금융 인사이트

LangChain은 고객의 요구에 맞춘 맞춤형 솔루션을 제공할 수 있어, 고객 경험을
크게 개선할 수 있다.

금융 서비스 제공업체 Morningstar는 LangChain을 사용해 방대한 재무 보고서와
시장 데이터를 분석하고, 이를 바탕으로 사용자 맞춤형 금융 인사이트를
제공하는 인텔리전스 엔진을 개발했다. 이 시스템은 금융 전문가들이 복잡한
질문에 대해 정확한 답변을 얻을 수 있도록 도와주며, LangChain의 실시간
데이터 통합과 맞춤형 프롬프팅 기능을 효과적으로 활용하고 있다.

## 이 프로젝트와의 접점

이 저장소엔 실제 금융/시장 데이터 소스가 없다(mova는 영화 도메인). 현재
`adapter/outbound/llm/`에는 PDF 요약 파이프라인(`pdf_loader_ollama_summarizer.py`)만
있고, `app/use_case/`의 `langchain_interactor.py`·`langgraph_interactor.py`는
아직 빈 파일이다 — LangChain 레이어 자체가 설계 전 단계다.

Morningstar 패턴(재무 보고서·시장 데이터 분석 → 맞춤 인사이트)을 옮기려면
먼저 다음이 정해져야 한다.

- 재무 보고서 같은 입력 문서를 어디서 가져올지 (현재 이 도메인엔 해당 문서
  소스가 없음)
- 기존 PDF 파이프라인(`pdf_loader_ollama_summarizer.py`)이 있긴 하나 재무
  문서에 특화된 처리는 아님 — 그대로 재사용할지, 별도 전처리를 둘지
- `domain/document_vector.py`가 있으나 금융 인텔리전스 질의응답에 맞는
  스키마는 아님

현재는 문서화만 하고 실제 구현은 보류.
