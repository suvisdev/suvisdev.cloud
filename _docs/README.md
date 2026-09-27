# `_docs/` 인덱스 (공통·인프라 문서)

> 이 저장소는 세 스택(`suvisdev/` 백엔드, `suvis/` 프론트, `gildle/` 모바일)이 한 저장소에
> 있고, 문서는 **성격별로 위치가 나뉜다** — 스택별 규칙은 각 스택 자신의 `_docs/`에 있고,
> 여기(루트 `_docs/`)는 **공통·인프라·워크스페이스 설정**만 둔다. 상세 배치 규칙은
> [`../CLAUDE.md`](../CLAUDE.md)의 "문서 배치 규칙" 표가 단일 근거(SSOT)다.

---

## 이 폴더에 있는 것

| 문서 | 내용 |
|------|------|
| [`ARCHITECTURE_BLUEPRINT.md`](ARCHITECTURE_BLUEPRINT.md) | 이 저장소에서 검증된 아키텍처 패턴(모듈러 모놀리식·클린 아키텍처 등)을 새 프로젝트에 그대로 적용할 때의 기준 문서 |
| [`ARDA_AWS_DEPLOY_GUIDE.md`](ARDA_AWS_DEPLOY_GUIDE.md) | Arda(seuk 팀 프로젝트) AWS 이전 실행 체크리스트 — 2026-09-04 완주, 잔여(SES·GPU 승인 등)는 PROGRESS 참고 |
| [`EXAONE_LOCAL_AI_SETUP.md`](EXAONE_LOCAL_AI_SETUP.md) | 로컬 GPU에 EXAONE Router/Worker(Ollama) + AWQ 직접 서빙 + mova 채팅용 QLoRA 재학습 파이프라인을 새 PC에서 그대로 재현하는 운영 문서(서빙 경로는 09-02 GGUF 전환 — 문서 상단 배너 참고) |
| [`INTERVIEW_QUESTIONS.md`](INTERVIEW_QUESTIONS.md) | 날짜별 학습·면접 대비 질문지 — 워크로그와 짝, 세션 마무리 때 그날 작업으로 5~10문항 추가 |
| [`SUBDOMAIN_MIGRATION_PLAN.md`](SUBDOMAIN_MIGRATION_PLAN.md) | 서브도메인 이사(seuk 전용) 결정 경위 + 개인 백엔드 EC2→노트북 이전 실행 기록 — 팀 이전은 09-04 완주(역사 기록) |
| [`SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`](SUVIS_ADMIN_MULTIAGENT_PROGRESS.md) | 어드민 대시보드 + 멀티에이전트(비전 02~08) 트랙 진행 상황 — 완료됨/백로그, 세션 재개용 |
| [`WORK_LOG_MOVA.md`](WORK_LOG_MOVA.md) | mova(영화 추천·채팅·게임) 날짜별 작업 일지 — 2026-08-19에 구 `WORK_LOG.md`에서 개명(과거 인용 대부분이 이 파일) |
| [`WORK_LOG_GILDLE.md`](WORK_LOG_GILDLE.md) | gildle(산책 경로) 날짜별 작업 일지 |
| [`WORK_LOG_MAINPAGE.md`](WORK_LOG_MAINPAGE.md) | 그 외 전부(메인페이지·어드민·인증·gildle 앱·인프라) 날짜별 작업 일지 |
| `.obsidian/` | 이 워크스페이스를 Obsidian 볼트로 열 때의 로컬 설정(심볼릭 링크 등) — 커밋되지만 개인 IDE 상태에 가까움 |

> mova 앱 관련 심층 조사(추천 품질 골든셋 · 오귀속 근본 원인 등)와 포트폴리오
> 문서(`MOVA_INTERVIEW_QA.md` · `MOVA_PORTFOLIO_SUMMARY.md` · `MOVA_Portfolio.pptx`)는
> 성격상 앱별 문서라 [`../suvisdev/apps/mova/_docs/`](../suvisdev/apps/mova/_docs/) 아래에 있다.
> `suvisdev/scripts/` CLI의 EC2 실행 가이드(`SCRIPTS_EXECUTION_GUIDE.md`)도 백엔드 문서라
> [`../suvisdev/_docs/`](../suvisdev/_docs/)에 있다(2026-08-28 이동).

---

## 스택별 규칙은 여기가 아니라 각자 `_docs/`에 있다

| 스택 | 전역 SSOT | 세부 규칙 |
|------|-----------|-----------|
| 백엔드(FastAPI, Clean Architecture) | [`suvisdev/CLAUDE.md`](../suvisdev/CLAUDE.md) | `suvisdev/_docs/`(엔티티·인증·DB 규칙), 앱별 `suvisdev/apps/<app>/_docs/`(ERD·도메인) |
| 프론트(Next.js) | [`suvis/CLAUDE.md`](../suvis/CLAUDE.md) | `suvis/_docs/`(React·디자인 규칙) |
| 모바일(Flutter) | `gildle/_docs/` | 카카오 OAuth·Android/iOS 하네스 |
| 경로별 자동 로드 규칙 | [`../.claude/rules/`](../.claude/rules/) | `typescript.md`·`api-standards.md`·`testing.md`·`security/*.md` — 해당 파일을 다룰 때 자동 적용 |

새 문서를 만들 때는 **성격에 맞는 위치**에 두고(위 표 또는 루트 `CLAUDE.md` 참고), 이
`_docs/`에는 여러 스택에 걸치거나 인프라 성격인 것만 추가한다.

---

## 2026-08-05 정리 기록

Cursor 하네스 시절 문서(`backend/`·`frontend/` 경로 전제, `DevOps/Backend/`·
`DevOps/Frontend/`·`타이타닉 개발/` 하위)가 실제 저장소 구조(`suvisdev/`·`suvis/`·`gildle/`)와
크게 어긋나 있어 정리했다:

- **삭제**(다른 곳에 이미 최신판이 있는 중복/폐기본): `TITANIC_ERD.md`(→
  `suvisdev/apps/titanic/_docs/titanic-erd.md`와 동일), `MOVA_ERD.md`+`mova-erd.png`(→
  `suvisdev/apps/mova/_docs/MOVA_ERD.md`가 v2/v3 리비전까지 반영된 최신판), `ENTITY_RULE.md`
  (→ `suvisdev/_docs/entity-rules.md`), `REACT_RULES.md`(→ `suvis/_docs/react-rules.md`,
  `suvis/CLAUDE.md`에서 실제 참조 중), `james_fastapi_context.md`(2026-05-07 초기 프로토타입
  기록, 현재 `suvisdev/apps/titanic/` 전면 재구축으로 완전히 대체됨).
- **병합**: 인덱스 `SUVISDEV_RULES.md` + 상세 `DevOps/Frontend/SUVISDEV_RULES.md` 두 파일을
  하나로 합침.
- **유지**: `EXAONE_LOCAL_AI_SETUP.md`(내용 자체는 여전히 정확), `WORK_LOG.md`·
  `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`·mova 추천 조사 문서 2건(이미 이번 세션들에서
  실측 기준으로 계속 갱신 중).
