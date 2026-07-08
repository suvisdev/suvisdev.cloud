# star_craft Hub 파이프라인 전략

> **역할:** star_craft는 스타-토폴로지의 허브다. Spoke(mova, titanic, viewer 등)에서 발생한 이벤트를 받아
> Graph DB(온톨로지·관계)와 Vector DB(의미 검색·RAG)로 전달하는 중앙 파이프라인을 담당한다.
> Spoke는 이 파이프라인을 직접 알지 못하고, 이벤트를 Hub로 발행할 뿐이다.

---

## 1. 기술 선택

| 역할 | 선택 | 이유 |
|------|------|------|
| **Graph DB** | Neo4j (Docker) | 온톨로지·엔티티 관계 모델링에 최적. `domain/ontology/`와 1:1 대응. Cypher 쿼리로 Spoke 간 관계 탐색 가능. |
| **Vector DB** | Qdrant (Docker) | Rust 기반, Docker 경량 이미지, REST + gRPC 지원. exaone 임베딩을 저장하고 RAG 파이프라인에 연결. |
| **임베딩 모델** | exaone3.5:2.4b (Ollama) | 이미 로컬 실행 중. `core/lol/t1_mid_faker_orchestrator.py`에서 프롬프트 생성, 별도 임베딩 API로 벡터 추출. |

---

## 2. Docker Compose 추가 서비스

`docker-compose.yaml`에 아래 두 서비스를 추가한다.

```yaml
services:
  # --- 기존 서비스 (backend, frontend, n8n) ---

  neo4j:
    image: neo4j:5
    ports:
      - "7474:7474"   # Browser UI
      - "7687:7687"   # Bolt (Python 드라이버)
    environment:
      - NEO4J_AUTH=neo4j/starcraft_hub   # .env로 분리 권장
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"   # REST API
      - "6334:6334"   # gRPC
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  n8n_data:
    external: true
  neo4j_data:
  qdrant_data:
```

> `.env`에 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `QDRANT_URL`을 추가하고
> `vauly_keymaker_secret_manager.py`에서 로드한다.

---

## 3. 파이프라인 아키텍처

```text
[Spoke 이벤트 발행]
  mova / titanic / viewer / silicon_valley
         │  (SpokeEvent — domain/events/)
         ▼
[star_craft inbound]
  adapter/inbound/api/v1/  ← HTTP POST (이벤트 수신)
  adapter/inbound/mcp/     ← MCP 채널 (향후 LLM 도구 연동)
         │
         ▼
[Use Case / Interactor]
  app/use_cases/
  ┌─────────────────────────────────────────────┐
  │ 1. 이벤트 파싱 → SpokeEventDto             │
  │ 2. 온톨로지 노드·관계 추출                  │
  │ 3. Graph DB 저장 (Neo4j)                    │
  │ 4. 임베딩 생성 (exaone via Ollama)           │
  │ 5. Vector DB 저장 (Qdrant)                  │
  └─────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
[Outbound Adapters]
  adapter/outbound/graph/    ← Neo4j 드라이버 (neo4j-driver)
  adapter/outbound/vector/   ← Qdrant REST 클라이언트 (httpx)
  adapter/outbound/publisher/ ← 결과 재발행 (선택)
```

---

## 4. 디렉터리 확장 계획

```text
apps/star_craft/
├── adapter/
│   ├── inbound/
│   │   ├── api/v1/
│   │   │   └── spoke_event_router.py      ← POST /star-craft/events
│   │   └── mcp/
│   │       └── hub_mcp_server.py          ← MCP 도구 노출 (향후)
│   └── outbound/
│       ├── graph/
│       │   └── neo4j_graph_repository.py  ← Cypher 쿼리 실행
│       ├── vector/
│       │   └── qdrant_vector_repository.py ← 컬렉션 upsert·검색
│       └── publisher/
│           └── event_publisher.py         ← (기존) n8n 발행
├── app/
│   ├── dtos/
│   │   ├── spoke_event_dto.py             ← SpokeEventDto, SpokeEventCommand
│   │   └── knowledge_dto.py               ← GraphNodeDto, VectorPointDto
│   ├── ports/
│   │   ├── input/
│   │   │   └── hub_ingest_use_case.py     ← ABC: ingest(event)
│   │   └── output/
│   │       ├── graph_repository.py        ← ABC: upsert_node, upsert_relation
│   │       └── vector_repository.py       ← ABC: upsert_point, search
│   └── use_cases/
│       └── hub_ingest_interactor.py       ← 메인 파이프라인 조율
├── domain/
│   ├── events/
│   │   └── spoke_events.py                ← SpokeEvent 공용 타입 (Spoke가 import)
│   └── ontology/
│       └── hub_ontology.py                ← 노드 레이블·관계 타입 상수
└── dependencies/
    └── hub_provider.py                    ← DI 조립
```

---

## 5. 데이터 흐름 상세

### 5-1. Graph DB (Neo4j)

Spoke 이벤트 → 온톨로지 노드·관계 추출 → Cypher `MERGE` 저장.

```text
예) mova "영화 저장" 이벤트
  (Movie {slug: "inception"}) -[:HAS_GENRE]-> (Genre {name: "SF"})
  (Movie {slug: "inception"}) -[:HAS_TAG]->   (Tag {name: "꿈"))
  (User {id: 42})             -[:PICKED]->     (Movie {slug: "inception"})
```

- 노드 레이블은 `domain/ontology/hub_ontology.py` 상수로 관리.
- `MERGE`(upsert) 전략으로 중복 없이 그래프 갱신.

### 5-2. Vector DB (Qdrant)

이벤트 페이로드 중 자연어 필드(제목, 시놉시스, 채팅 메시지 등) → exaone 임베딩 → Qdrant 컬렉션 저장.

```text
컬렉션 예시:
  hub_movies    ← Movie 텍스트 임베딩 (slug + title + synopsis)
  hub_chats     ← 채팅 메시지 임베딩 (RAG 검색용)
  hub_reviews   ← 리뷰 텍스트 임베딩
```

- 임베딩: Ollama `/api/embeddings` 엔드포인트 사용 (`model: exaone3.5:2.4b`).
- Qdrant `upsert` 시 payload에 `spoke`, `entity_id` 등 원본 메타데이터 포함.

### 5-3. RAG 조회 (역방향 — 향후)

```text
Spoke 조회 요청
  → star_craft MCP / API
  → Qdrant semantic search (상위 k 후보)
  → Neo4j 관계 확장 (후보 주변 그래프)
  → exaone 컨텍스트 주입 → 응답 생성
  → Spoke 반환
```

---

## 6. 연결 설정 (`.env` 추가 항목)

```dotenv
# Graph DB
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=starcraft_hub

# Vector DB
QDRANT_URL=http://localhost:6333

# Ollama (임베딩)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=exaone3.5:2.4b
```

`vauly_keymaker_secret_manager.py`에 `neo4j_uri`, `qdrant_url`, `ollama_base_url` 필드를 추가한다.

---

## 7. 구현 순서 (Phase)

| Phase | 작업 | 완료 기준 |
|-------|------|-----------|
| **P1** | docker-compose에 Neo4j·Qdrant 추가 | `docker compose up` 후 양쪽 UI 접속 확인 |
| **P2** | Keymaker에 연결 정보 추가 | `get_keymaker().neo4j_uri` 반환 확인 |
| **P3** | `graph_repository.py` ABC + `neo4j_graph_repository.py` 구현 | `MERGE` 노드 1개 저장 테스트 |
| **P4** | `vector_repository.py` ABC + `qdrant_vector_repository.py` 구현 | 컬렉션 생성·upsert·search 테스트 |
| **P5** | `hub_ingest_interactor.py` 조율 로직 | `SpokeEvent` 1개 end-to-end 저장 확인 |
| **P6** | `spoke_event_router.py` HTTP 엔드포인트 | POST 요청 → 양 DB 반영 확인 |
| **P7** | RAG 조회 엔드포인트 / MCP 도구 노출 | exaone 답변 생성 확인 |

---

## 8. 스타-토폴로지 규칙 준수

| 방향 | 허용 |
|------|------|
| Spoke → `domain/events/spoke_events.py` import | ✅ |
| Spoke → star_craft 나머지 레이어 직접 import | ❌ |
| star_craft → Spoke import | ❌ |
| star_craft → `core.*` import | ✅ |

Spoke는 오직 `star_craft.domain.events.spoke_events`의 이벤트 타입만 알고,
HTTP POST로 Hub 엔드포인트에 이벤트를 발행한다.
Hub는 그 이벤트를 Graph·Vector DB에 기록하고 결과를 자체 보관한다.
