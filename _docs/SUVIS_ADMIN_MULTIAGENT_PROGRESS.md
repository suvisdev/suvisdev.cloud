# SUVIS 어드민 대시보드 + 멀티에이전트 진행 상황

컨텍스트가 끊길 경우를 대비한 재개용 메모. 완료된 작업은 상세 로그 대신
**위치만** 남긴다(중복 기록 방지). 관련 상세 지시서:
- `suvisdev/_docs/RBAC_agent_dashboard.md` (RBAC + 어드민 대시보드 H0~H4)
- `suvisdev/apps/ontology/_docs/00_COMMON_conventions.md` + `01~08_*.md` (에이전트별 지시서)

---

## 완료됨 (상세는 각 문서 참고, 여기선 재기록 안 함)

- **어드민 대시보드**: 홈/사용자/앱관리/통계/캘린더/설정 전 화면 구현 + 실 연동
  (`suvis/app/admin/*`, `suvis/lib/admin-*-api.ts`). RBAC 가드(`require_admin`,
  `AdminAuthGate`)까지 포함.
- **01(이미지 분류, 포스터→장르)**: H0~H6 전체 완료. `01_image_classifier_agent.md` §7.
- **07(Echo, 감정분석)**: H0~H6 전체 완료(NSMC 기반, val acc 87.75%).
  `07_sentiment_analysis_agent.md` §5~§10.
- **06(Sentinel, 이상 탐지)**: H0~H6 전체 완료(CLIP 제로샷 포스터 판별 +
  Laplacian 블러, `/vision/upload` 게이트). `06_anomaly_detection_agent.md`
  §5~§6.9. 미결 백로그는 아래 "다음 / 남은 작업" 참고.
- **02~08 H0 스캐폴딩**: 포트/인터페이스 껍데기 7개 태스크 전부 생성 완료
  (실제 추론 어댑터는 없음).
- **03(Loom, 시맨틱 분할)**: **제외 확정(2026-07-27)**. 용도 재정의("보도 유무/폭")
  까지 검토 후 관문0 실측 → 보도 신호 자체가 서울 OSM에 없음(`sidewalk=*`
  0.4~1.2%, 커버리지 보도/도로 = 0.04, `width` 전무). 04·08과 동급 정식 제외.
  상세: `03_semantic_segmentation_agent.md` §5.4, WORK_LOG 2026-07-27.
- **alembic 마이그레이션 체인 베이스라인 누락 수정(2026-07-27)**: `users`/
  `groups`/`admins`, mova 전체 테이블, `dispatch_adress`, `titanic_passengers`,
  `vision_uploads` 등이 `create_all()`로만 존재하고 체인엔 CREATE가 없던 문제.
  베이스라인 마이그레이션 신설로 완전히 빈 DB에서 `alembic upgrade head`
  성공 검증 완료(EC2 임시 컨테이너). 상세: WORK_LOG 2026-07-27 [3].
- **PDF 업로드→추출→요약 파이프라인(execsuite, 구 silicon_valley, 2026-07-27, `pdf_loader_*` 네이밍)**:
  `POST /api/v1/pdf/summarize` — neo4j-graphrag PdfLoader 추출 + EXAONE(Ollama)
  요약 + `pdf_loader_documents` 테이블 저장, inbound router~outbound repository
  전 계층 완성. 실 DB 마이그레이션 실행/Ollama 연동 실사용 테스트는 미검증.
  상세: WORK_LOG 2026-07-27 [4]·[5](네이밍 환원).
- **execsuite(구 silicon_valley) LangChain 채팅 파이프라인(2026-07-28)**: `POST /api/v1/langchain/chat`
  — semantic_router_interactor(ontology)로 의도 판단 후 LangChain LCEL 체인이
  destination별 시스템 프롬프트로 답변 생성. 클린 아키텍처 전 계층 완성,
  semantic_router의 `HubRagError` 미처리로 500 plain-text 새던 버그도 수정.
  모델은 최초 ChatOllama(exaone3.5:2.4b)로 구현했다가 같은 날 `ChatGoogleGenerativeAI`
  (Gemini, `core.matrix.Keymaker` 키 재사용)로 교체 — 실제 응답 확인 완료.
  상세: WORK_LOG 2026-07-28.
- **기존 실패 테스트 수정(2026-07-28)**: `apps/mova/tests/test_import_interactor.py`
  2건 — `ImportInteractor` 생성자에 `box_office`/`hub_rag`가 추가된 뒤 테스트가
  안 따라가서 실패하던 것, `AsyncMock()` 인자 추가로 수정. `test_llm_error_handling.py`는
  이미 통과 상태였음(기록이 stale). 8개 전부 통과 확인.
- **어드민 백엔드 인증 공백 — dispatch watcher/judge/spam/adress 감사(2026-07-28)**:
  watcher·judge는 `/myself` 스캐폴딩 스텁뿐(위험 없음), spam은 프론트/백엔드
  어디서도 호출 안 하는 미사용 코드(위험 낮음). **adress는 실제 문제 발견** —
  `search`/`upload`에 인증이 전혀 없었고, 어드민 UI(`admin/dispatch/contacts`)뿐
  아니라 LESSON 공개 데모(`suvis/app/mail/contacts`, 로그인 개념 없음)도 같은
  엔드포인트를 호출 — 익명 방문자가 실제 주소록 DB에 쓰기 가능했음. 2026-07-27과
  동일 패턴으로 `require_admin` 추가 + 프론트 프록시 2개(`search`/`upload`
  route.ts)·어드민 클라(`admin/dispatch/contacts/page.tsx`)가 세션 Bearer
  전달하도록 수정. **`suvis/app/mail/contacts`(공개 레슨 데모)는 이제 401 —
  이 페이지 자체를 지울지/막을지는 별도 결정 필요(아래 백로그).**
- **CLAUDE.md 응답 언어 지침 추가(2026-07-28)**: 항상 한국어로만 답변, 다른 언어
  사용 금지를 루트 `CLAUDE.md`에 명시.
- **`test_send_email_interactor.py` 실패 2건 수정(2026-07-28)**: `SendEmailInteractor.send()`가
  이메일 품질 개선을 위해 `orchestrator.generate()`에 `system=` 키워드 인자를
  추가한 게 실제 기능인데, 테스트 2건이 예전(위치 인자 하나) 시그니처를
  가정하고 있어 깨졌던 것 — 테스트를 실제 호출 형태에 맞게 수정. 14개 전부 통과.
- **PyJWT/langchain-ollama 미설치 해소(2026-07-28)**: `/home/a/.venv`에서
  `require_admin` import가 안 되던 문제를 `PyJWT[crypto]==2.10.1`,
  `langchain-ollama==1.1.0` 개별 설치로 해결. `apps/mova/tests` + `apps/dispatch`
  전체 47개 테스트 통과 확인(이전엔 jwt 없어 수집 자체가 실패하던
  `test_whoami_router.py`도 포함).
- **`catboost`/Python 3.14 빌드 문제 해소 + `pip install -r requirements.txt`
  전체 성공(2026-07-28)**: `catboost==1.2.8`→`1.2.10`으로 올렸더니 Python
  3.14용 사전빌드 wheel이 존재해 빌드 에러 없이 설치됨. 전체 `requirements.txt`
  설치가 끝까지 성공(torch-cu126 포함). `.import_linter_cache`/`.mypy_cache`
  (18M)/`.pytest_cache`/`.ruff_cache` 정리(전부 재생성 가능한 도구 캐시, git
  미추적).
- **`apps/silicon_valley` → `apps/execsuite` 이름 변경(2026-07-28)**: `admin`은
  이미 다른 의미(어드민 대시보드/RBAC)로 쓰이고 있어 충돌 우려로 `execsuite`로
  확정. 102개 파일 rename + 46개 파일 import·외부 3곳(`main.py`,
  `alembic/env.py`, `.importlinter`) 전부 치환. `execsuite_router`/`main.py`
  import 검증 완료.
- **`suvisdev/labs/` 04(자세 추정)·08(영상 분류) 독립 실습 데모(2026-07-28)**:
  `apps/`와 완전히 분리된 고립 영역(`main.py` 미등록, `.importlinter` 미포함).
  Port는 참조 구현(실제 편입 시 그 앱 컨벤션대로 재배치), DTO는 도메인
  중립이라 공유 가능하다고 README에 명시. GPU 없어 학습 없이 사전학습 모델
  추론만 — 04는 YOLOv8n-pose(3.3M), 08은 torchvision s3d(8.3M, 가장 가벼운
  옵션으로 실측 비교 후 선택). 둘 다 실제 실행해 결과 확인 완료. 상세:
  WORK_LOG 2026-07-28 [6].
- **`suvisdev/labs/semantic_segmentation/` 03(시맨틱 분할) 추가(2026-07-28)**:
  04·08과 동일 패턴. 04·08과 달리 03은 "용도 없음"이 아니라 "용도(서울 보도
  검출)는 있었는데 검증 데이터(OSM sidewalk 태그 0.4~1.2%)가 없어서" 막힌
  케이스임을 README에 구분해 명시. 모델은 torchvision segmentation 4종
  실측 비교 후 가장 가벼운 `lraspp_mobilenet_v3_large`(3.2M, Pascal VOC —
  도로/보도 클래스 자체가 없어 막힌 용도와 구조적으로 무관) 선택. 실제
  실행해 결과 확인 완료(bus 31.0%, person 12.2% 정상 검출).
- **mova 부팅 자동 작업 `ENABLE_MOVA_STARTUP` 플래그(2026-07-28)**: 집(GPU/
  EXAONE)·EC2(GPU 없음, Gemini) 두 배포 환경에서 mova의 TMDB 시드·chat_trend/
  KOFIC 스케줄러(전부 Ollama 의존)를 EC2에서 코드 변경 없이 끌 수 있게
  `main.py` `lifespan()`에 플래그 추가(기본값 true, 하위호환). mock으로
  DB/Ollama 없이 분기만 격리 검증 — false일 때 3개 함수 전부 미호출+
  "비활성화됨" 로그, 미설정 시 기존대로 전부 호출됨을 확인. 부수 발견:
  `seed_assistants_if_empty` import가 존재하지 않는 모듈 참조하는 기존 버그
  (아래 백로그).
- **titanic 도메인 테스트 4개 재작성 + 실제 버그 2건 수정(2026-07-28)**: 조사
  결과 단순 리네임 드리프트가 아니라 도메인 재설계(관련 VO·엔티티·깨진
  테스트가 전부 같은 커밋에서 한꺼번에 업로드됨)였음을 확인. mova/gildle도
  "개념당 VO 하나" 컨벤션을 써서 지금 titanic 도메인(`PassengerIdentity`/
  `Survived`)이 실제 컨벤션과 일치함을 검증 후, `test_korean_ai_adapter.py`
  삭제(중복 고아) + 나머지 3개 삭제 후 41개로 새로 작성(frozen 불변성,
  DDD 동등성, DIP 어댑터 스왑 포함 — titanic이 기준선이라 다른 앱이 참고할
  모범 형태로). 작성 중 `summary()`/`to_orm_fields()`가 존재하지 않는
  `identity.age`를 참조하는 실제 버그 발견해 수정. `apps/titanic/tests`
  44개 전부 통과.
- **`seed_assistants_if_empty` 죽은 코드 제거(2026-07-28)**: 실제 조사 결과
  리네임이 아니라 한 번도 구현된 적 없는 기능(repository에 count/insert
  메서드·기본 시드 데이터 전부 없음)으로 확인 — `main.py`에서 해당
  try/except 블록 통째로 제거. `ENABLE_MOVA_STARTUP` 두 시나리오 재검증
  결과 WARNING 완전히 사라지고 플래그 동작은 그대로 정상.

---

## 진행 중 (현재 액티브)

없음. (03 제외 확정으로 이번 트랙의 액티브 조사 종료. 착수 대기 항목은
아래 "다음 / 남은 작업" 참고.)

---

## 다음 / 남은 작업 (백로그)


- **CLIP 모델(`openai/clip-vit-base-patch32`) 다운로드 hang(2026-07-28 발견)**:
  `apps/ontology/test` 전체 실행 시 Hugging Face Hub에서 이 모델(Sentinel
  이상탐지가 씀) 다운로드가 1시간 넘게 멈춤(`.incomplete` 파일 확인) —
  네트워크 문제로 추정, 프로세스 강제 종료로만 대응. 재현·원인 조사 안 함.
- **비전 02·05**(아래 감사표): 02 용도 결정, 05 용도+VRAM 전략(외부 GPU 분리?) 필요.
- **06 미결**: Sentinel 소프트 플래그 **저장 지속화 + 어드민 오버라이드 엔드포인트**
  (저장 계층 정리 후 — S3 배선인데 AWS 미연결, DB 폴백 `VisionRepository` 미배선).
- **시크릿 (a)**: pydantic-settings 도입 시 mova·ontology 키 접근 함께 이관
  (단독 실행 금지 — WORK_LOG 2026-07-24 [2순위](a)).
- **S3**: AWS 실연결(버킷+키 세팅) 후 Tank 단일 경로 실 업로드 검증.
- **`suvis/app/mail/contacts` 공개 레슨 데모 처리(2026-07-28 신규)**: adress
  엔드포인트에 `require_admin`을 걸면서 이 페이지는 이제 업로드 시도 시 401만
  받는다. 페이지 자체를 지울지, 로그인 요구 안내로 바꿀지, 별도 더미 데이터로
  분리할지 제품 결정 필요.
- **어드민 백엔드 인증 공백**: (2026-07-27 대응) 가드를 `shared/security/require_admin.py`로
  이동 후 dispatch `email/telegram/discord` POST·`receive` GET/DELETE, harvester
  `scrape/crawl/sites`에 `require_admin` 추가 + 프론트 프록시/클라가 세션 Bearer를
  백엔드까지 전달(3계층). 상세 WORK_LOG 2026-07-27 [2]. **2026-07-28 추가**:
  `watcher/judge/spam/adress` 전수 감사 완료 — watcher/judge는 위험 없는 스텁,
  spam은 미사용 코드, **adress는 실제 무인증 쓰기/조회 취약점이라 수정 완료**
  (위 "완료됨" 참고). `receive` POST는 외부 인입이라 의도적으로 무인증 유지.

---

## 참고: 02~08 적합성 감사 (2026-07-23, `00_COMMON_conventions.md` §8)

06의 실패(기법 먼저·용도 나중)를 기준으로 재감사한 결과.

| # | 이름 | 상태 |
|---|------|------|
| 02 | Argus(객체 검출) | 보류 — 용도 위험/데이터 불확실, 제품 결정 전까지 착수 안 함 |
| 03 | Loom(분할) | **제외**(2026-07-27) — 관문0 실측: 보도 신호가 서울 OSM에 없음(문서 배너) |
| 04 | Atlas(자세 추정) | **제외** — mova/gildle에 용도 없음(문서 배너) |
| 05 | Prisma(이미지 생성) | 보류 — 용도 불확실 + 하드웨어 위험(SD1.5 LoRA vs lora-server VRAM 겹침) |
| 06 | Sentinel(이상 탐지) | **완료**(H0~H6, `/vision/upload` 게이트) |
| 07 | Echo(감정분석) | **완료**(H0~H6) |
| 08 | Chronos(영상 분류) | **제외** — mova/gildle에 용도 없음(문서 배너) |

## 참고: VRAM 정책 (확정, `00_COMMON_conventions.md` §1.1)

`lora-server`(mova 채팅용 EXAONE-2.4B AWQ)가 상시 기동 → **모든 학습 전
`systemctl --user stop lora-server`**, 학습 후 `start` + `:8200/health` 확인 필수.
`nvidia-smi` free 수치만 믿지 말 것(WSL2 계측 불안정, 290MB↔7975MB 편차 사례).
