# Neo4j Docker 설치 전략

`ranggraph-harness.md`가 제안한 LangGraph retrieve 노드의 GraphRAG(하이브리드
검색)를 실제로 쓰려면 Neo4j 서버가 먼저 떠 있어야 한다. 이 문서는 그 서버를
이 프로젝트의 기존 방식대로 docker-compose에 추가하는 전략만 다룬다 —
`docker-compose.yaml`/`.env` 실제 수정은 하지 않는다.

## 현재 상태 (재확인)

- `docker-compose.yaml`에 neo4j 서비스 없음. 로컬·EC2 모두 실행 중인
  인스턴스 없음(`neo4j-hanress.md` 확인 내용과 동일).
- `.env`엔 `NEO4J_PASSWORD`만 있고 `NEO4J_URI`/`NEO4J_USER`는 없음.
- `neo4j-graphrag`(→ `neo4j` 드라이버 포함)는 이미 설치돼 있음
  (`requirements.txt`).
- `apps/ontology/_docs/star-craft-pipeline.md`에 참고용 docker-compose
  스니펫(`neo4j:5`, `NEO4J_PLUGINS=["apoc"]`)이 이미 있음 — 이 전략은 그
  계획을 그대로 이어받아 구체화한다.

## 왜 Docker인가

이 프로젝트는 이미 backend/auth/db/redis/pgadmin/cloudflared를 전부
docker-compose로 관리한다. Neo4j도 같은 방식으로 두면:

- 기동·재기동·버전 고정이 나머지 서비스와 일관된다.
- Ollama(EXAONE)처럼 호스트 상시 프로세스로 관리할 필요가 없다 — Neo4j는
  GPU가 필요 없어 컨테이너로 완전히 격리해도 된다.
- 로컬(개발)과 EC2(운영) 양쪽에 동일한 compose 파일로 배포할 수 있다.

## docker-compose.yaml 추가안

```yaml
  # 6. Neo4j — GraphRAG(ranggraph-harness.md)용 그래프 DB
  # 실행: docker compose --env-file suvisdev/.env up -d neo4j
  neo4j:
    image: neo4j:5.26-community   # 실제 적용 시 최신 5.x 안정 패치로 재확인
    restart: unless-stopped
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc"]'   # GraphRAG 적재 시 apoc.periodic.iterate 등 대비, 예방적으로 켜둠
    ports:
      - "7474:7474"   # Browser UI
      - "7687:7687"   # Bolt (Python 드라이버·backend 연결)
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
```

`volumes:` 최상위 블록에 `db_data`/`redis_data`/`pgadmin_data`와 같은 자리에
추가:

```yaml
volumes:
  db_data:
  redis_data:
  pgadmin_data:
  neo4j_data:
  neo4j_logs:
```

## `.env` 추가안

```dotenv
NEO4J_URI=bolt://localhost:7687   # 호스트(스크립트·cypher-shell 확인용)에서 접속할 때
NEO4J_USER=neo4j
# NEO4J_PASSWORD는 이미 있음 — 그대로 재사용
```

## backend가 실제로 Neo4j를 호출하게 될 때(GraphRAG 코드 작성 시점)

`DATABASE_URL`/`REDIS_URL`과 같은 패턴이 적용된다 — 호스트에서 쓰는
`NEO4J_URI=bolt://localhost:7687`는 컨테이너 안에서는 자기 자신을 가리켜
못 붙으므로, `backend` 서비스의 `environment:`에서 서비스명으로 덮어써야
한다.

```yaml
  backend:
    environment:
      # ...(기존 DATABASE_URL/REDIS_URL 등)
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      neo4j:
        condition: service_healthy
```

## 기동·검증 절차

1. `docker compose --env-file suvisdev/.env up -d neo4j`
2. `neo4j-hanress.md`의 "1. Python 드라이버로 확인" 코드를 그대로 실행해
   `verify_connectivity()` 통과 확인.
3. `.env`에 위 `NEO4J_URI`/`NEO4J_USER`를 추가(비밀번호는 기존 값 재사용).
4. `neo4j-hanress.md`의 예시 `CREATE` 문으로 노드·관계 쓰기까지 검증하고,
   `MATCH (n) RETURN count(n)` 등으로 조회 확인.

## 데이터 지속성

`neo4j_data` 네임드 볼륨 — `db_data`/`redis_data`와 동일한 패턴으로
컨테이너를 내렸다 올려도 데이터가 유지된다. 백업 전략은 이번 스코프
밖(운영 전환 시 별도 문서).

## `ranggraph-harness.md`와의 연결

`ranggraph-harness.md`의 "단계적 도입 순서" 3번("Neo4j 실배포 후 retrieve
노드를 GraphRAG로 교체·보강")이 이 문서가 다루는 작업이다. 이 전략대로
Neo4j가 뜨고 나면, 그 문서가 제안한 retrieve 노드(Text-to-Cypher + 벡터
하이브리드 검색)를 실제로 구현할 수 있다.

## 남은 결정 사항

- `neo4j:5.26-community`는 예시 태그다 — 실제 적용 시점의 최신 5.x 안정
  버전으로 재확인 필요.
- EC2는 GPU가 없는 인스턴스라 `backend`처럼 `nvidia` device reservation은
  필요 없지만, Neo4j 힙 메모리가 다른 서비스와 RAM을 나눠 쓰기 충분한지는
  실제 배포 전 확인 필요.
- APOC 플러그인이 실제로 필요한지는 아직 예방적 판단일 뿐 — GraphRAG
  구현이 표준 Cypher만으로 충분하면 빼도 된다.

이 문서는 전략만 기록한다 — `docker-compose.yaml`/`.env` 실제 반영과 기동은
사용자 확인 후 별도로 진행한다.
