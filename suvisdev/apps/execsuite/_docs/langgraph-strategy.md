# LangChain+pgVector → LangGraph+Neo4j 확장 전략

`langgraph-harness.md`(왜 LangGraph·GraphRAG인가)와 `neo4j-strategy.md`(Neo4j
docker-compose 설치안)가 각각 아키텍처와 인프라를 다룬다. 이 문서는 그 둘을
어떤 순서로 도입할지 — 4단계 로드맵과 단계별 선행조건 — 만 정리한다.

## 왜 지금 확장하는가

지금 execsuite의 챗봇 흐름(`langchain_chat_router` → `langchain_interactor` →
`langchain_chat_engine_repository`)은 `ChatPromptTemplate` → `ChatGoogleGenerativeAI`
→ `StrOutputParser`로 이어지는 단일 선형 LCEL 체인이다. "단순 문서 검색
(Vector) 중심"에서 "지식 관계망(Graph) 중심의 지능형 흐름 제어(Agent)"로
가려면 아래 네 가지가 순서대로 필요하다.

1. 관계 데이터를 저장할 그래프 DB(Neo4j)
2. Vector 검색과 Graph 검색을 함께 쓰는 Hybrid Retrieval
3. 선형 체인을 조건 분기·루프가 가능한 그래프(LangGraph `StateGraph`)로 재설계
4. 검색 결과가 부족하면 스스로 재검색하는 에이전틱 피드백 루프

## 4단계 로드맵

### 1단계 — Neo4j 도입 및 지식 그래프 구축 (1-2주 차)

- Neo4j DB 인스턴스 기동 — `neo4j-strategy.md`의 docker-compose 추가안을 그대로
  적용(로컬은 Docker, EC2도 같은 compose 파일).
- `langchain-neo4j` 패키지 설치 확인(현재 `requirements.txt`에는 `neo4j-graphrag`만
  있고 `langchain-neo4j`는 없음 — 필요 여부 확인 후 추가).
- pgVector에 있는 텍스트(Chunk)에서 `LLMGraphTransformer` 등으로 핵심 개념(Node)과
  관계(Edge)를 추출해 Neo4j에 적재하는 파이프라인을 설계.
- **선행조건**: `.env`에 `NEO4J_URI`/`NEO4J_USER` 추가(`NEO4J_PASSWORD`는 이미 있음).
- **완료 기준**: `neo4j-hanress.md`의 `verify_connectivity()` 통과 + 샘플 문서
  하나를 Node/Edge로 변환해 Neo4j에 적재·조회 성공.

### 2단계 — Hybrid Retrieval 구현 (2-3주 차)

- pgVector(유사도 검색)와 Neo4j Cypher(관계 검색)를 같은 질문에 대해 각각
  실행하고 결과를 통합하는 리트리버를 구성.
- 키워드 추출 기반으로 Cypher 쿼리를 만드는 파이프라인(`GraphCypherQAChain` 등)을
  검증 — 아직 실서비스 라우팅에 붙이지 않고 독립적으로 정확도만 확인.
- **선행조건**: 1단계에서 지식 그래프가 최소 한 도메인 분량 채워져 있어야 함.
- **완료 기준**: 다단계 관계(Multi-hop) 질문 샘플 셋에서 pgVector 단독 대비
  Hybrid 결과가 더 나은지 비교 확인.

### 3단계 — LangChain 체인 → LangGraph 전환 (3-4주 차)

- `langgraph-harness.md`의 "제안하는 흐름"을 실제 설계로 확정 — `StateGraph`
  정의(질문 분석 → 라우팅 → 검색 → 검증 → 답변생성), 조건부 엣지로 분기 구현.
- `semantic_router_interactor`(ontology)가 destination과 함께 "reasoning 필요"
  신호를 반환하도록 확장 — 이 신호로 기존 선형 체인(`langchain_interactor`)과
  새 `StateGraph` 경로를 가른다.
- **선행조건**: 2단계 Hybrid Retrieval이 retrieve 노드로 그대로 꽂을 수 있는
  형태로 검증돼 있어야 함.
- **완료 기준**: `reasoning 필요` 질문이 `StateGraph` 경로를 타고, 그렇지 않은
  질문은 기존 `langchain_chat_engine_repository` 경로를 그대로 타는 것을 확인.

### 4단계 — 에이전틱 피드백 루프 및 고도화 (4주 차 이후)

- 검증(verify) 노드가 "불충분"으로 판단하면 retrieve 노드로 되돌아가는 루프를
  추가 — 최대 재시도 횟수로 종료 계약을 반드시 건다(무한 루프/비용 폭증 방지).
- 대화 상태·체크포인트를 저장할 Checkpointer 적용 여부 결정(세션 간 상태 유지가
  필요한지 이 서비스 요구사항에 맞춰 판단).
- 필요 시 검색 과정에서 얻은 새 관계를 Neo4j에 다시 써넣는 업데이트 루프 검토.
- **선행조건**: 3단계 `StateGraph`가 분기 없이 단방향으로는 안정 동작해야 함.
- **완료 기준**: 재시도 루프가 최대 횟수에서 정상 종료되고, 실패 시에도
  사용자에게 명확한 응답(무한 대기 없음)이 나가는 것을 확인.

## 이 프로젝트와의 접점 (현재 상태 재확인)

- `requirements.txt`에 `langgraph`/`langgraph-checkpoint`/`langgraph-prebuilt`,
  `neo4j-graphrag==1.18.0`가 이미 설치돼 있지만 코드베이스 어디서도 쓰이지
  않는다. `langchain-neo4j`는 아직 없음 — 1단계에서 필요 여부 확인.
- Neo4j 서버 자체가 아직 없다 — `.env`에 `NEO4J_PASSWORD`만 있고
  `NEO4J_URI`/`NEO4J_USER`는 없음, `docker-compose.yaml`에 neo4j 서비스 없음
  (`neo4j-strategy.md` 참고).
- `apps/ontology/app/use_cases/semantic_router_interactor.py`는 지금
  `crud`/`rag`/`general` 3갈래만 분류한다 — 3단계가 요구하는 "reasoning 필요"
  신호는 아직 없음.
- execsuite의 챗봇 경로(`langchain_chat_router` → `langchain_interactor` →
  `langchain_chat_engine_repository`)는 분기·루프·재시도가 전혀 없는 단일
  선형 체인 — 4단계가 요구하는 종료 계약(최대 재시도) 설계 자체가 아직 없다.

## 남은 결정 사항

- Hybrid Retrieval의 통합 방식(pgVector 결과와 Cypher 결과를 어떤 가중치·순서로
  LLM에 넘길지)은 2단계 착수 시점에 별도로 정해야 한다.
- Checkpointer 적용 여부(4단계)는 이 서비스가 세션 간 대화 상태를 얼마나
  유지해야 하는지에 달려 있다 — 아직 결정된 바 없음.
- 위 주차 수치는 목표치이며, 1단계(Neo4j 실배포)가 늦어지면 이후 단계도
  순연된다 — 1단계가 나머지 세 단계 전부의 선행조건이다.

이 문서는 도입 순서와 단계별 선행조건·완료 기준만 기록한다 — 실제 구현
(Neo4j 배포, Hybrid 리트리버, `StateGraph` 작성, 피드백 루프)은 각 단계 착수
시점에 별도 작업으로 진행한다.
