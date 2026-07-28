# LangGraph 하네스

## 왜 LangChain 체인에 LangGraph를 더하는가

LangChain의 체인(Chain)은 A → B → C로 흐르는 단방향 파이프라인이다. 지금
execsuite의 `rangchain_chat_engine_repository.py`(`ChatPromptTemplate` →
`ChatGoogleGenerativeAI` → `StrOutputParser`)가 정확히 이 구조다 — 순서가
고정돼 있어 "답이 부족하니 검색 단계로 되돌아가기" 같은 루프나, 판단에
따라 다른 경로를 타는 분기가 불가능하다.

LangGraph는 이 선형 구조를 그래프(노드+엣지)로 바꿔 아래를 가능하게 한다.

1. **선형 구조의 한계 극복** — 조건에 따라 다른 노드로 가거나(분기), 같은
   노드로 되돌아가는(루프) 흐름을 표현할 수 있다.
2. **정교한 상태 관리(State Management)** — 대화 기록뿐 아니라 중간 판단,
   검색된 문서, 남은 재시도 횟수 같은 것들을 하나의 State 객체에 담아 그래프
   전체가 공유·갱신한다.
3. **복잡한 에이전트 제어 및 루프** — 오류가 나면 스스로 고치는
   Self-correction, 조건 분기, 사람 개입(Human-in-the-loop)이 필요한
   프로덕션급 로직을 안정적으로 제어할 수 있다.
4. **멀티 에이전트 협업** — 리서치 노드·검증 노드·답변 작성 노드처럼 여러
   역할이 상호작용하는 구조를 코드로 표현하기 쉽다.

## GraphRAG를 위한 Neo4j 활용법

Neo4j는 데이터 간 관계를 노드·엣지로 저장하는 그래프 DB로, GraphRAG의
핵심 인프라다. GraphRAG는 비구조화 텍스트에서 엔티티·관계를 뽑아 지식
그래프를 만들고, 이를 근거로 다단계 추론(Multi-hop Reasoning)을 하는
기법이다.

1. **지식 그래프 구축(Ingestion)** — LangChain의 `LLMGraphTransformer` 같은
   도구로 문서를 분석해 핵심 개념(노드)과 관계(엣지)를 추출, `Neo4jGraph`에
   저장한다.
2. **Text-to-Cypher 검색** — 사용자의 자연어 질문을 `GraphCypherQAChain` 등이
   Neo4j의 쿼리 언어인 Cypher로 변환한다.
3. **그래프 탐색 + 하이브리드 검색** — 변환된 Cypher로 다중 홉(Multi-hop)
   이웃 노드를 가져오거나, Neo4j의 벡터 인덱스와 결합해 하이브리드(그래프+
   의미론적) 검색을 한다.
4. **정교한 답변 생성** — DB에서 뽑은 명시적 관계·맥락을 LLM에 주입해,
   추측·환각(Hallucination) 없는 답변을 만든다.

## 장단점

**장점**: 루프·분기·상태 공유가 필요한 복잡한 워크플로우를 명시적인
그래프로 표현할 수 있어 프로덕션 안정성이 높다. 노드 단위로 역할을 쪼개기
때문에 멀티 에이전트 협업 구조를 코드로 옮기기 쉽다.

**단점**: State 스키마·노드·엣지를 설계하는 초기 비용이 LangChain 단일
체인보다 크다. 조건 분기·루프 종료 조건을 잘못 설계하면 무한 루프·비용
폭증으로 이어질 수 있어, 최대 재시도 횟수 같은 종료 계약이 필수다.

## 이 프로젝트와의 접점

**지금 있는 것**:
- `apps/ontology/app/use_cases/semantic_router_interactor.py` —
  `crud`/`rag`/`general` 3갈래로만 분류한다(`qwen_intent_classifier.py`
  `_DESTINATIONS`). "reasoning"(다단계 추론이 필요한 질문) 갈래는 아직
  없다.
- `apps/execsuite/adapter/outbound/repositories/rangchain_chat_engine_repository.py` —
  `ChatPromptTemplate → ChatGoogleGenerativeAI → StrOutputParser` 단일
  선형 LCEL 체인. 분기·루프·재시도 없음.
- `requirements.txt`에 `langgraph`/`langgraph-checkpoint`/`langgraph-prebuilt`,
  `neo4j-graphrag==1.18.0`가 이미 설치돼 있지만, 코드베이스 어디서도 실제로
  쓰이지 않는다.
- Neo4j 서버 자체는 아직 미배포다 — `.env`에 `NEO4J_PASSWORD`만 있고
  `NEO4J_URI`/`NEO4J_USER`는 없음(`neo4j-hanress.md` 참고). 그래서 GraphRAG
  절의 내용은 지금 당장 구현 가능한 게 아니라, Neo4j 연결이 선행돼야 하는
  목표 아키텍처다.

**제안하는 흐름**(문서화만, 미구현):

```text
질문 입력
   │
   ▼
semantic_router_interactor (ontology)
   │  destination 판단: crud / rag / general
   │  + "reasoning 필요 여부" 신호 추가 (다단계 추론·비교·근거 검증이
   │    필요한 rag 질문인지 판단)
   │
   ├─ reasoning 불필요 ──► 기존 rangchain_chat_engine_repository.py
   │                       (LangChain 단일 체인, 지금 그대로)
   │
   └─ reasoning 필요 ────► LangGraph StateGraph
                              │
                    State: question, destination, entities,
                           grounding, retrieved_docs,
                           retry_count, verified
                              │
                              │
                              ▼
                        retrieve 노드
                  (RAG/GraphRAG 하이브리드 검색)
                              │
                              ▼
                        generate 노드
                    (LangChain LLM 호출로 답변 생성)
                              │
                              ▼
                         verify 노드
                    (근거 대비 답변 충분한지 판단)
                              │
              ┌───────────────┴────────────────┐
              │ 불충분(retry_count 남음)         │ 충분(verified=True) 또는
              │ → retrieve로 루프백              │ retry_count 소진 → 종료 계약
              ▼                                 ▼
        (retrieve 노드로)                   최종 답변 반환
```

**단계적 도입 순서(제안)**:
1. `semantic_router_interactor`가 destination과 함께 "reasoning 필요"
   신호를 반환하도록 확장(Neo4j 없이도 `rag`의 기존 벡터 검색만으로 우선
   루프/재시도 구조부터 검증 가능).
2. `execsuite`에 `rangchain_reasoning_graph.py` 같은 새 어댑터를 두고,
   `LangGraph StateGraph`로 retrieve → generate → verify → (재시도 or 종료)
   구현. 최대 재시도 횟수로 종료 계약을 반드시 건다.
3. Neo4j 실배포 후 retrieve 노드를 GraphRAG(Text-to-Cypher + 벡터 하이브리드)
   로 교체·보강.

이 harness는 설계 방향만 기록한다 — 실제 구현(semantic_router 확장,
새 그래프 어댑터, Neo4j 연결)은 별도 작업으로 진행한다.
