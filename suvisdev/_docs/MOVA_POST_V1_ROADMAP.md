# MOVA v1 완결 판정 및 완결 후 로드맵

## Meta

**목적**: `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(현재 백로그 순위)와
`_docs/WORK_LOG.md`(일자별 실행 기록) 위의 **상위층 문서**. v1 완결 판정 기준,
완결 이후 남은 백로그 스냅샷, 신규 사이클 후보, 취업 어필 문서화 트랙을
한 곳에 모은다.

**PROGRESS/WORK_LOG와의 관계**
- PROGRESS: 진행 순위 · 완료된 항목의 인덱스. 라이브 백로그.
- WORK_LOG: 일자별 실행의 상세 기록. append-only.
- **본 문서**: 그 위의 상위 로드맵. 매 사이클 종결마다 갱신하는 살아있는
  문서. 새 백로그를 창작하지 않고, PROGRESS·WORK_LOG·품질 검증 문서에
  실측 근거가 있는 항목만 옮겨 적는다.

**MOVA v1 완결 정의**: 아래 Section A의 5축이 전부 ✅이면 v1 종결로 판정한다.
"결함 제로"가 아니라 **결함이 백로그로 관리되고 있는 상태**를 완결로 본다
(Section A-5 참고).

**표기 규칙**
- ✅ 완결 / ⏳ 미완 / ⚠️ 결정 대기
- 애매하면 실 문서 링크를 근거로 첨부
- 결정 대기 항목은 결정 축·트레이드오프를 명시
- 근거 문서 없는 항목은 뺀다(사용자가 새로 지정한 카테고리는 "근거 부재"로 명시)

---

## Section A: MOVA v1 완결 판정 체크리스트

| # | 축 | 현 상태 | 판정 | 근거 문서 |
|---|-----|---------|------|-----------|
| A-1 | 핵심 UX 루프 폐쇄 (검색→후보→카드→상세→리뷰→취향→재추천) | 취향 벡터 재정렬 배포 완료(2026-08-18). 리뷰 저장 시 BG 임베딩 + taste 재계산 체이닝 + 추천 재정렬까지 폐쇄 루프 | ✅ | PROGRESS "취향 벡터 재정렬(2026-08-18)", "mova 리뷰 이해 파이프라인 β/γ 사이클(2026-08-11)" |
| A-2 | 데이터 정합성 (크론 3건·백필·HNSW 인덱스·레거시 정리) | movies embedding·review embedding·taste vectors 크론 3건 KST 03:00/30/45 안전망 가동, 잔여 0 확인. HNSW 인덱스 + `enable_seqscan=off` 세션 힌트. 레거시 무태그 12편 삭제 완료 | ✅ | `_docs/SCRIPTS_EXECUTION_GUIDE.md`, PROGRESS "0.5순위 HNSW", "레거시 무태그 12편(2026-08-18)" |
| A-3 | 보안/인증 하드닝 (mova 리뷰 IDOR·mova/chat user_id 신뢰) | mova 리뷰 Phase A(POST/PATCH `require_user`·IDOR 대조·upsert IntegrityError 구조 해결), watched 게이트, mypage/watchlist/picks feedback IDOR 전수 수정 완료 | ✅ | PROGRESS "mova 리뷰 API 보안 하드닝 Phase A(2026-07-31)", "리뷰 watched 게이트(2026-08-04)"; `.claude/rules/security/auth.md` §5 |
| A-4 | 운영 관측성 (크론 로그 리다이렉트·백필 idempotent) | 크론 3건 전부 `>> ~/*.log 2>&1` 표준 형태로 등록. 백필 3종 전부 `IS NULL` 필터로 idempotent. 로그 인프라 부재 발견(2026-08-11) 이후 표준 문서화 | ✅ | `_docs/SCRIPTS_EXECUTION_GUIDE.md` §"왜 이 문서가 필요한가" |
| A-5 | 알려진 결함 관리 (제로가 목표 아님) | PROGRESS.md에 착수·결정 대기 항목이 우선순위와 함께 명시적으로 관리됨. 각 항목이 "왜 남았는지" 결정 축 명시 | ✅ | PROGRESS "다음 / 남은 작업(백로그)" 전 섹션 |

**판정**: 5축 전부 ✅ → **MOVA v1 완결(2026-08-18 시점)**. 다음 사이클부터
Section B·C·D의 축을 새 스코프로 진행한다.

---

## Section B: v1 스코프 내 완결 후 남은 백로그

### B-1 코드 백로그 (PROGRESS 순위 그대로 인용)

| 항목 | 상태 | PROGRESS 순위 | 근거 요약 |
|------|------|---------------|-----------|
| 취향 재정렬 후속 — alpha 별점 결합 튜닝 | ⏳ | 재정렬 후속 백로그 | 현재는 순수 코사인. `α·cosine + (1-α)·norm(rating)` A/B 실측 후 alpha 결정. 별점이 후보 12편 압축 시점에 이미 적용돼 이중 계산 회피가 우선순위였음 |
| 취향 재정렬 후속 — 후보 window 확대 | ⏳ | 재정렬 후속 백로그 | `search_tag_catalog(limit=16)` · LLM 3편 pick 구조. taste vector 있는 유저에게 window 확대 검토 |
| `search_tag_catalog` 후보 생성 개선 | ⚠️ 부분 | QUALITY_PHASE1 §9(2026-08-18 정정) | (1) 배우 이름 미지원 · (2) top-12 rating 컷 · (4) `origin_country` **3건은 이미 해소**(26adfec/26adfec/b07c64b). (3) 키워드 OR→AND 결합만 미해소. 원 4가지 결함 표기의 stale 정정은 §9 참고 |
| intent_extraction 배우 인식 (옵션 A) | ✅ 2026-08-18 완결 | QUALITY_PHASE1 §9.3 (정정) — `_has_hard_signal` 완화로 장르 하나만으론 Gemini 스킵 안 함. 두 축 결합 결함(정규식 미인식 + Gemini 스킵)에서 후자 해소. 옵션 B(정규식 확장)/C(actors.name DB lookup)는 실측 결과 부족하면 추가 트랙 |
| hub_knowledge 재임베딩 실행 | ⚠️ | 1순위 | Ollama 벡터(2014행) vs Gemini 쿼리 벡터가 의미 공간 불호환. 프로덕션 데이터 삭제·재적재라 사용자 판단 대기. 실행 명령·선행조건 준비 완료 |
| `EMBEDDING_BACKEND=gemini` 스위치 켜기 | ⚠️ | 1순위 남은 것 ① | 재임베딩 없이 flip만 하면 오히려 조용한 오응답(차원 같아 에러 없이 잘못된 이웃) — flip은 재임베딩과 원자적으로 진행해야 함 |
| 영화-컬렉션 배정 API/CLI 신설 | ✅ | 2026-08-18 완결(7순위 해소) — `PATCH/DELETE /mova/collections/{slug}/movies` + `scripts/assign_collection_cli.py`. 8순위 실질 창구 확보. 상세: WORK_LOG 2026-08-18 |
| 컬렉션 큐레이션 지속 확장 | ⚠️ 부분(3/6, v3 남음) | 8순위 — v2(2026-08-18) 감독 필모 3개(spielberg/tarantino/ridley-scott, 33편) 완료. 총 배정 44→77편. v3 D/E/F(korean-cinema/animation-masters/horror-classics)는 rating=5.0 노이즈 오염 확인 → KR 성인 잔여 purge 선행 후 재시도 |
| KR 성인 잔여 purge v2 (신규) | ⏳ | 8순위 선행 | 2026-08-14 130편 purge 이후에도 rating=5.0 top-N에 성인물 잔여("섹귀·피지컬 뷁·윤율의 사내 불륜·비키니바" 등 실측). 130편 purge 필터(키워드 regex + rating<4.0) 확대 재적용 필요 |
| rating 노이즈 완화 (신규) | ⏳ | 8순위 v3 대안/보완 | rating 컬럼이 소수 평가에도 5.0을 반환 — 큐레이션 rating DESC 정렬에서 오답 유발 실증. vote_count 기반 재정렬 또는 rating 상한 컷(예: 4.5) 도입 검토 |
| KR 카탈로그 필터 완화(`vote_count_gte` 50 또는 20) | ⚠️ | "TMDB KR 유명 영화 대량 수집 후속" | 신규 확보량이 낮음. 게임 품질 트레이드오프(초성 게임 필터 `rating ≥ 3.3`와 이중 방어). 확대 여부는 결정 필요 |

### B-2 운영/인프라 백로그

| 항목 | 상태 | 근거 |
|------|------|------|
| Neo4j GraphRAG 활용 코드 부재 | ⏳ | PROGRESS "Neo4j GraphRAG 활용 코드 부재(2026-08-04 재정의)" — Movie 40/Person 427 등 노드 데이터는 있으나 `apps/mova`·`apps/ontology` 어디에도 이걸 읽는 코드가 없음. 어느 앱이 언제 쓸지 설계 미착수 |
| `movies.embedding` 백필 자동화 유지 관측 | ✅(자동화) | 크론 등록 완료, 잔여 0 확인. 사용자 개입 불필요, 주기적 로그 확인만 |
| Gemini 무료 티어 쿼터 완화 | ⚠️ | PROGRESS 9순위 (b) 완료 — Gemini 2회→1회, 429 재시도 1회. 유료 티어 전환은 제품·비용 결정으로 사용자 판단 대기 |
| 노트북 LoRA 복구 + `RECOMMENDATION_BACKEND` 원복 | ⚠️ | PROGRESS 5순위 — 노트북 GPU/터널 직접 접근 필요, 원격 조치 불가 |
| cloudflared `api.suvisdev.cloud` 관찰 결론 | ✅ | 2026-08-18 판정 종결. 6.7일 9538 샘플 FAIL 620건 중 초일(08-11) 527·08-13 87·08-14 1건, **08-15~08-18 4일간 0건**. 자연 해소로 확정. 상세: WORK_LOG 2026-08-18 |

### B-3 결정 대기 항목 (사용자 판단 필요)

| 항목 | 결정 축 | 트레이드오프 | 근거 |
|------|---------|--------------|------|
| hub_knowledge 재임베딩 실행 여부 | 프로덕션 데이터 삭제 승인 | 재적재 시간·Gemini 쿼터 vs 벡터 검색 폐쇄 지속 | PROGRESS 1순위 남은 것 ② |
| mova 문의 이메일 확정 | 개인 gmail 유지 vs 전용 support 주소 | 대응 부담 · 브랜드 인상 | PROGRESS "mova 법적 페이지 후속" |
| LLM 챗 3개(titanic/smith·execsuite/langchain·contents/soccer) 무인증 유지 | 레슨 데모 개방성 vs 남용(Gemini 과금) | 학습 UX vs 비용 리스크 | PROGRESS "LLM 챗 엔드포인트 3개 무인증+무 rate-limit(2026-08-04)" |
| `suvis/app/mail/contacts` 처리 방향 | 페이지 삭제 · 로그인 안내 · 더미 데이터 분리 | 공개 데모 유지 vs 401 잔재 정리 | PROGRESS "`suvis/app/mail/contacts` 공개 레슨 데모 처리(2026-07-28)" |
| Gemini 유료 티어 전환 여부 | 사용자 규모 예상 · 월 비용 | 무료(분당 15) 유지 vs 유료 확장성 | PROGRESS 9순위 남은 것 (a) |
| 비전 02·05 용도 결정 | 실제 사용 계획 vs 실습 데모 유지 | 착수 자원 vs 방치 | PROGRESS "비전 02·05" |
| KR 카탈로그 필터 완화 vs 게임 품질 유지 | 카탈로그 규모 vs 초성 게임 품질 | 확장 vs 저품질 유입 | PROGRESS "TMDB KR 유명 영화 대량 수집 후속" |

### B-4 감사/조사 트랙

| 항목 | 상태 | 근거 |
|------|------|------|
| `bulk_import_movies.py` upsert_movie except(76~84행) rollback — 재현 시험 | ⏳ | PROGRESS "조사 종결(2026-08-05)" — 76~84행은 "재발 없음 관찰"이지 "검증"이 아님. 우선순위 낮음 |
| 폰 카메라 → S3 업로드 실기기 검증 | ⏳ | PROGRESS "폰 카메라 → S3 업로드 실기기 검증(2026-08-03 신규)" — 폰 adb 연결 필요, access token 10분 TTL 만료 시 자동 refresh 미구현 |
| susu 카카오 로그인 iOS 실빌드 검증 | ⏳ | PROGRESS "susu 카카오 모바일 로그인 — iOS 실빌드 검증(2026-08-03)" — Android E2E 성공, iOS는 Info.plist만 넣고 미검증. 맥 필요 |
| mova 추천 챗 화면 실기기/데스크톱 실행 검증 | ⏳ | PROGRESS "mova 추천 챗 화면 — 실기기/데스크톱 실행 검증(2026-08-03 신규)" |
| CF Tunnel public → Zero Trust Access 잠금 | ⏳ | PROGRESS "mova 추천 — CF Tunnel public 상태를 Zero Trust Access로 잠그기(2026-08-05)" — 현재 URL만 알면 누구나 호출 가능(왕복 검증 목적으로 의도적 개방) |

---

## Section C: 신규 사이클 후보 (v2 or 별도 프로젝트)

각 항목마다 "별도 프로젝트 vs MOVA 내부 피처" 판단 근거를 실 문서에서 인용.

### C-1 RAG 검색 (hub_knowledge 재임베딩 이후)

- **위치**: MOVA 내부 피처.
- **근거**: PROGRESS 1순위 "hub_knowledge 재임베딩 실행" + QUALITY_PHASE1
  §4 "hub_knowledge 임베딩 백필 절차(사전 조사만 — 미실행)". 배관은 이미
  구현돼 있고(`ChatInteractor.hub_rag.search_movies` 우선 → 없을 때만
  `search_tag_catalog` 폴백) 데이터만 채우면 자동 활성화되는 상태.
- **판단**: 코드가 이미 `apps/mova`·`apps/ontology`에 있고 flip + 재임베딩만
  남은 상태라 명확히 MOVA 내부 사이클. 별도 프로젝트로 분리할 근거 없음.
- **선행조건**: B-3의 "hub_knowledge 재임베딩 실행 여부" 사용자 판단.

### C-2 리뷰 감정 분석 (aspect-based 취향 매칭)

- **위치**: MOVA 내부 피처.
- **근거**: PROGRESS 1-c순위 "MOVA 리뷰 이해 파이프라인" 다음 순서 2 —
  **"감정 축 — ontology `echo_sentiment_adapter`를 Spoke→Hub 포트로 연결"**.
  `07(Echo, 감정분석)` H0~H6 전체 완료(NSMC 기반, val acc 87.75%)가
  PROGRESS "완료됨"에 이미 있음 → 어댑터 구현체는 존재, 배선만 남음.
- **판단**: 온톨로지 Hub의 `echo_sentiment_adapter`가 이미 학습 완료된
  상태라 MOVA에서 Spoke→Hub 포트로 연결하는 것으로 그침. 별도 프로젝트
  분리 근거 없음.
- **주의**: "aspect-based"(감정 대상별 분리)는 사용자 지정 프레이밍이며
  현재 `07_sentiment_analysis_agent.md`가 aspect-based까지 다루는지는 미확인
  (본 문서에서 확인 안 함) — 착수 전 별도 조사 필요.

### C-3 챗봇 (학원 커리큘럼 대응)

- **위치**: **근거 문서 부재 — 사용자 지정 카테고리**. 기존 `apps/mova/chat`
  이 이미 챗봇이고, execsuite `langchain/chat`·contents `soccer/chat`·
  titanic `smith/chat` 등 학습 목적 챗 데모가 이미 있음.
- **판단 보류**: "학원 커리큘럼 대응"이 무엇을 의미하는지 명세가 없어
  기존 챗 확장인지 별도 프로젝트인지 판정 불가. **착수 전 사용자에게
  범위 명세 요청 필요**(어느 학원의 어떤 커리큘럼, MOVA 챗 확장인지
  새 앱인지).

---

## Section D: 취업 어필 문서화 트랙

**주의**: 이 섹션 전체가 **사용자 지정 카테고리로 실 문서 근거 없음**.
프로젝트 코드·문서에는 이력서·면접·발표 자료가 존재하지 않음(2026-08-18 확인).
따라서 아래는 항목 정의만이고, 실행 전에는 사용자와 스코프 합의 필요.

| 항목 | 착수 조건 | 참고할 실 문서 |
|------|-----------|----------------|
| 이력서용 MOVA 요약(5개 스토리 축) | Section A의 5축을 스토리로 재구성. "무엇을·왜·측정된 성과·의사결정" 형태 | Section A + PROGRESS 완료 목록 |
| 면접 예상 질문 대비 노트 | 어느 회사·직군인지 사용자 지정 필요. 원본 근거는 실제 문제 해결 기록 | WORK_LOG(각 세션의 오류·막힌 점 섹션), `MOVA_RECOMMENDATION_MATCHING_ROOT_CAUSE.md`(근본 원인 조사 사례) |
| 포트폴리오 발표 자료 | 청중(면접관·팀 리뷰) 지정 필요. 지표(카탈로그 규모·골든셋 pass rate 등)는 실측 값 사용 | QUALITY_PHASE1 §6·§7·§8 재검증 표 (통과 6→9→8, 국가·연도 필터 이후 0카드 5→2건 등) |

**공통 원칙**(사용자 지정 착수 전에도 유효): 실측 근거 있는 지표만 사용,
"~할 수 있다"보다 "~했다"의 완료형·수치 근거로 서술.

---

## Section E: 우선순위 정렬 및 다음 착수 지점

**지금 착수하기 좋은 3개**(사용자 결정 대기 없이 코드/문서로 즉시 진행 가능):

1. ~~**영화-컬렉션 배정 API/CLI 신설**~~ — **완료(2026-08-18)**: 위 B-1
   참고. 8순위(컬렉션 큐레이션 확장)의 실질 창구 확보. 다음 후보는
   그 8순위(테마별 배치 큐레이션) 또는 B-1의 alpha 별점 결합 튜닝.

2. ~~**`search_tag_catalog` 배우 조인 추가**~~ — **이미 완료(2026-08-06
   26adfec) · 2026-08-18 재확인**: QUALITY_PHASE1 §9 참고. 남은 잔여
   실패(#5·#7)의 원인은 intent 계층으로 이동 — 후속 후보는 "intent 배우
   인식 개선"(B-1 신규).

3. ~~**cloudflared 24h 관찰 결론**~~ — **완료(2026-08-18)**: 자연 해소
   판정. 위 B-2 참고. 다음 착수 지점 슬롯 하나 비었으니 후속 후보는
   다음 사이클 결정 시 재선정.

**결정 대기가 풀리면 착수**(B-3 우선):
- hub_knowledge 재임베딩 → C-1 RAG 검색 자동 활성화 → QUALITY_PHASE1의
  실패 6건 중 커버리지 부족 계열(§7.3 원인과 별개 축) 재검증.
- Gemini 유료 여부 → 임베딩 하루 쿼터 제약 해소 여부.

**신규 사이클(v2)로 넘어갈 시점**:
- Section B-1 상위 3개 + Section E 상위 3개 처리 완료 후 남는 것이
  "결정 대기(B-3) + 실기기 검증(B-4)"만이면 C 섹션으로 진입.

---

## 갱신 이력

| 날짜 | 갱신 요지 | 근거 사이클 |
|------|-----------|-------------|
| 2026-08-18 | 문서 신설. v1 5축 판정 = 5/5 ✅. Section B·C·D·E 초판 | 취향 벡터 재정렬 배포 완료 |
| 2026-08-18 | cloudflared 관찰 종결(자연 해소) — B-2 ✅ 갱신, Section E-3 슬롯 오픈 | 6.7일 실측 판정 |
| 2026-08-18 | QUALITY_PHASE1 §7 stale 정정(§9 신설) — 배우 조인·`origin_country`·레거시 12편 해소 반영, 잔여 결함이 (3) 다중 장르 AND + intent 계층으로 이동함 명시 | 프로덕션 실측 재검증 |
| 2026-08-18 | 영화-컬렉션 배정 API/CLI 신설(7순위 완결) — B-1 표 및 Section E-1 반영 | 12파일 신규/수정, 신규 테스트 6건 |
| 2026-08-18 | 컬렉션 큐레이션 v2 부분 완결(8순위 3/6) — 감독 필모 3개 신규, 총 배정 44→77편. B-1에 KR 성인 잔여 purge v2 + rating 노이즈 완화 백로그 추가 | 감독 3개(spielberg/tarantino/ridley-scott) 배정 + D/E/F rating=5.0 노이즈 오염 실측 |
| 2026-08-18 | intent_extraction 배우 인식 옵션 A 완결 — `_has_hard_signal` 완화, QUALITY_PHASE1 §9.3 원인/결과 반전 서술 정정 | 두 축 결합 결함 규명 · 테스트 4→7건 · mova 216 pass |
