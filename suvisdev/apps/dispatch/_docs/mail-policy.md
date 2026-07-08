# Gmail → n8n → 백엔드(pgvector) 메일 수신 파이프라인

> Gmail로 들어온 메일을 n8n이 감지해 백엔드(FastAPI)로 전달, `receive_router.py`가 받아서
> Ollama 임베딩(pgvector)까지 저장하는 실제 운영 중인 파이프라인. 구축 과정에서 겪은 시행착오와
> 최종 채택된 구조를 정리한 문서.

---

## 0. 실제 아키텍처 (현재 운영 중)

```
Gmail 새 메일
   │
   ▼
n8n "Gmail Trigger" (폴링, 1분 간격)   ← 실제로 쓰는 방식. Push(Pub/Sub)는 폐기됨 (§4 참고)
   │
   ▼
n8n "HTTP Request" 노드
   │  POST http://backend:8000/api/v1/dispatch/receive
   │  body: sender={{$json.From}}, subject={{$json.Subject}}, body={{$json.snippet}}
   ▼
receive_router.py (dispatch 앱)
   │
   ▼
receive_interactor.py
   │  subject+body → Ollama(nomic-embed-text)로 임베딩 생성 시도
   │  실패해도(NULL) 메일 저장은 계속 진행
   ▼
receive_repository.py → dispatch_inbox 테이블 (pgvector, embedding vector(768))
```

Docker Compose 구성 요소(`cloudsuvisdev-*`): `backend`(8000) · `frontend`(3000) · `n8n`(5678) · `pgvector`(5432, Postgres+pgvector 확장) · `neo4j`(7474/7687, 현재 미사용) · `redis`(6379) · `cloudflared`.

---

## 1. 실제 엔드포인트

| 레이어 | 파일 |
|--------|------|
| Router | `dispatch/adapter/inbound/api/v1/receive_router.py` |
| Schema | `dispatch/adapter/inbound/api/schemas/receive_schema.py` — `ReceiveRequestSchema`(sender·subject·body) / `ReceiveItemSchema` |
| Dto | `dispatch/app/dtos/receive_dto.py` — `ReceiveSaveCommand` / `ReceiveItem` |
| Interactor | `dispatch/app/use_cases/receive_interactor.py` — 임베딩 생성·실패 폴백 담당 |
| Output Port | `dispatch/app/ports/output/receive_port.py`, `embedding_port.py` |
| Repository | `dispatch/adapter/outbound/repositories/receive_repository.py` |
| 임베딩 어댑터 | `dispatch/adapter/outbound/llm/ollama_embedding_adapter.py` — Ollama `/api/embed` 호출 |
| ORM | `dispatch/adapter/outbound/orm/receive_orm.py` — `DispatchReceiveOrm`, 테이블명 `dispatch_inbox` (레거시 이름 유지) |

```text
POST   /api/v1/dispatch/receive   { sender, subject, body } → 저장 + 임베딩
GET    /api/v1/dispatch/receive   → 목록 조회 (최신순, 최대 200건)
DELETE /api/v1/dispatch/receive/{id}
```

**프론트엔드**: `suvis/app/admin/dispatch/receive/page.tsx` (관리자 "수신함" 탭) ↔ `suvis/app/api/dispatch/receive/route.ts` (프록시).

---

## 2. 임베딩 (pgvector)

- 모델: **`nomic-embed-text`** (768차원). `exaone3.5:2.4b`는 Ollama 기준 `capabilities: ["completion"]`뿐이라 임베딩 요청 시 항상 501 에러 — 애초에 임베딩 불가능한 모델이었음. `ollama pull nomic-embed-text`로 교체.
- 컬럼: `dispatch_inbox.embedding vector(768)`, nullable. 마이그레이션: `alembic/versions/20260702_0003_add_dispatch_inbox_embedding.py`.
- **임베딩 실패는 메일 저장을 막지 않는다** — `ReceiveInteractor`가 `DispatchError`를 잡아서 `embedding=NULL`로 저장. n8n이 실시간으로 진짜 메일을 보내는 엔드포인트라 데이터 유실보다 임베딩 누락이 낫다는 판단.
- 확인 방법:
  ```bash
  docker exec cloudsuvisdev-pgvector-1 psql -U postgres -d starcraft -c \
    "SELECT id, subject, embedding IS NOT NULL AS has_embedding, vector_dims(embedding) AS dims FROM dispatch_inbox ORDER BY id DESC LIMIT 5;"
  ```
  또는 Docker Desktop → `pgvector` 컨테이너 → **Exec** 탭에서 `psql -U postgres -d starcraft` 직접 접속, 혹은 DBeaver/pgAdmin으로 `localhost:5432`(user `postgres` / db `starcraft`) 접속.

---

## 3. n8n 워크플로우 실제 구성 ("My workflow", 활성화 상태)

| 브랜치 | 트리거 | 구성 |
|--------|--------|------|
| 메일 수신 (사용 중) | Gmail Trigger (Every Minute) | → HTTP Request → `POST .../dispatch/receive` |
| 메일 발송 (사용 중) | Webhook (`dispatch-email`) | → Send a message(Gmail) → Send a text message(Telegram) → Respond to Webhook |

### 3.1 폴링(Gmail Trigger) 설정값
- Credential: 기존 Gmail OAuth2 계정 재사용
- Poll Times: **Every Minute**
- Event: **Message Received**
- Simplify: **ON**
- 뒤에 붙는 HTTP Request 노드: `sendBody: true`, Body Parameters `sender={{$json.From}}`, `subject={{$json.Subject}}`, `body={{$json.snippet}}`

> ⚠️ `{{$json.snippet}}`은 Gmail의 짧은 미리보기 텍스트라 항상 앞부분만 잘려서 저장된다. 전체 본문이 필요하면 `snippet` 대신 `text`/`html` 필드로 바꿔야 함 (아직 미적용).

---

## 4. Push(Pub/Sub) 방식 — 시도했으나 폐기됨

과거 실시간 수신을 위해 아래 구조를 구축했었다: `Webhook1 → Code in JavaScript → HTTP Request2(Gmail history 조회) → Code in JavaScript1 → HTTP Request3(메시지 조회) → HTTP Request4(백엔드 전송)`, 그리고 `Schedule Trigger → HTTP Request1`(watch 7일 만료 갱신).

**폐기 이유**: Cloudflare Tunnel(`cloudflared`) 컨테이너의 실제 라우팅이 `api.suvisdev.cloud → http://host.docker.internal:8000`(백엔드)로만 되어 있고, **n8n(5678, `/webhook/gmail-push`)으로 가는 공개 HTTPS 경로가 아예 없었다.** 즉 Google Pub/Sub이 n8n의 웹훅을 호출할 방법 자체가 없어서, 실제로 살아있던 건 폴링뿐이었다. Push 브랜치와 watch 갱신 브랜치는 워크플로우에서 완전히 삭제했다.

**다시 시도하려면**:
1. Cloudflare Zero Trust 대시보드 → Tunnels → Public Hostname에 `n8n:5678`로 가는 라우트를 별도로 추가해야 함 (대시보드 접근 필요, 코드/CLI로는 불가 — Named Tunnel이 `TUNNEL_TOKEN` 기반 dashboard-managed 방식이라 로컬 config 파일이 없음).
2. 이후 아래 순서로 재구축:
   - **공개 HTTPS 확보**: `n8n` 컨테이너로 가는 Cloudflare 라우트 연결
   - **n8n Webhook 노드**: Method POST, Path `gmail-push`
   - **Pub/Sub 토픽·구독 생성**: 토픽에 `gmail-api-push@system.gserviceaccount.com`에게 Publisher 권한 부여 필수, 구독 전송 유형은 **Push**, 엔드포인트 = `<터널 URL>/webhook/gmail-push`
   - **watch 등록**: `POST https://gmail.googleapis.com/gmail/v1/users/me/watch`, body `{"topicName": "projects/<PROJECT_ID>/topics/<TOPIC>", "labelIds": ["INBOX"]}` — 7일 만료, Schedule Trigger로 매일 재호출 필요
   - Pub/Sub 알림엔 `historyId`만 오고 메일 내용이 없어서 별도 Gmail API 재조회 단계가 반드시 필요함

---

## 5. 메일 발송 파이프라인 (`email_router.py`)

수신과 별개의 독립 흐름. `POST /api/v1/dispatch/email` → `SendEmailInteractor` → EXAONE(로컬 Ollama)이 본문·제목 생성 → n8n webhook(`dispatch-email`) → Gmail 발송 + Telegram 알림.

- **본문**: `_SYSTEM` 프롬프트로 생성. 소형 모델(exaone3.5:2.4b) 특성상 `[프로젝트 이름]` 같은 대괄호 플레이스홀더, `**굵게**`/`##제목` 마크다운, 심지어 요청을 스팸으로 오인해 경고 문구를 생성하는 등 프롬프트만으로는 신뢰할 수 없는 출력이 나옴 → `_sanitize_body()`로 정규식 후처리(플레이스홀더 제거·마크다운 스트립)를 추가했으나, **모델이 아예 내용을 거부하고 `****`로 마스킹하거나 엉뚱한 경고문을 본문/제목에 넣는 경우는 후처리로 못 잡음** (알려진 한계 — 근본 해결은 더 큰 모델로 교체).
- **제목**: 사용자가 안 적으면 LLM에게 별도로 한 줄 생성 요청(`_generate_subject`), 실패 시 `"메일 발송"` 리터럴로 폴백.

---

## 6. 백엔드 로컬 개발 환경 주의사항

- **Docker + Windows 바인드 마운트 + `uvicorn --reload`**: 기존 파일 *수정*은 핫리로드가 잘 잡지만, **새 파일 생성**은 감지를 못 하는 경우가 있다 → `docker restart cloudsuvisdev-backend-1`로 강제 재시작.
- **requirements.txt 변경 후**: 이미지에 반영 안 됨. 급하면 `docker exec cloudsuvisdev-backend-1 pip install <package>`로 핫패치 후 컨테이너 재시작, 정식 반영은 이미지 재빌드 필요.
- **Alembic 마이그레이션**: 로컬 pgvector 컨테이너에는 자동 적용 안 됨 → `docker exec cloudsuvisdev-backend-1 python -m alembic upgrade head`로 직접 실행해야 함.
- **PowerShell**: bash의 `\` 줄바꿈이 안 먹힌다. `docker exec ... psql -c "..."` 같은 명령은 한 줄로 이어서 입력.
- **n8n 워크플로우 저장**: 노드 설정 창을 닫는 것과 워크플로우 저장은 별개. 반드시 캔버스에서 `Ctrl+S`.

---

## 7. 비용

| 구성요소 | 비용 |
|---|---|
| n8n 셀프호스팅 | 무료 (커뮤니티 에디션) |
| Gmail API (폴링/watch) | 무료 |
| Ollama(로컬 임베딩·LLM) | 무료 (로컬 실행) |
| Cloudflare Tunnel | 무료 |

---

## 8. 완료 현황

- [x] n8n 셀프호스팅, Docker Compose 구성
- [x] Gmail Trigger 폴링 → `POST /api/v1/dispatch/receive` 종단 연결 (실제 메일 수신 확인됨)
- [x] `dispatch_inbox` 테이블 + pgvector `embedding` 컬럼, nomic-embed-text 임베딩 파이프라인
- [x] 임베딩 실패 시 NULL 폴백 (메일 저장 우선)
- [x] 관리자 프론트(`/admin/dispatch/receive`) 실데이터 연동
- [x] 메일 발송(`/api/v1/dispatch/email`) + LLM 본문/제목 생성 + 후처리 sanitizer
- [ ] Push(Pub/Sub) 방식 — 폐기, 재구축 시 §4 참고
- [ ] 본문 전체 텍스트 수신 (현재 `snippet`만 저장)
- [ ] LLM 콘텐츠 거부/마스킹(`****`) 문제 — 더 강력한 모델(Gemini 등) 교체 검토 필요
