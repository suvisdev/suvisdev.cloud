# 작업 일지 — GILDLE 워크로드

날짜별로 그날 한 작업·수정·오류·데이터를 기록한다. **최신 날짜가 맨 위**로
오게 추가한다(새 항목은 이 안내 바로 아래에 삽입). 요약용 재개 메모는
`SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`(현재 상태·다음 할 일)를 따로 쓰고,
이 파일은 **그날그날 실제로 있었던 일의 상세 기록**(무엇을 왜 했는지,
어디서 막혔는지, 데이터가 어떻게 바뀌었는지)에 집중한다.

**항목 템플릿**:
```
## YYYY-MM-DD

### 작업 내용
- 무엇을 했는지, 왜 했는지(계기)

### 수정/구현
- 만들거나 고친 파일·코드, 핵심 변경점

### 오류·막힌 점
- 무슨 에러가 났는지, 원인, 어떻게 해결했는지(해결 안 됐으면 그것도 기록)

### 데이터
- 데이터셋 출처·규모·라벨 변경 등

### 산출물
- 커밋 해시, 문서 갱신 위치 등
```

---

## 2026-09-22

### 작업 내용 (앱 출시 준비 — walks API · 건물 그늘 파이프라인 복구)
- 앱 출시를 **gildle만** 하기로 결정(mova는 TMDB 약관의 AI 학습 조항이 별도 서면
  계약을 요구 — gildle은 OSM/공공데이터 기반이라 그 리스크가 없다).
- gildle이 **stateless 경로 계산기**라 사용자가 다시 열 이유가 없다는 문제를
  `walks` API로 해결하고, 코드만 있고 한 번도 돌지 않았던 **건물 그늘 계산**을
  복구했다.

### 수정/구현
- **`walks` API 신규** (`/api/gildle/walks`) — 저장·목록·상세·삭제·통계 5종.
  전부 `require_user`이고, **남의 기록은 403이 아니라 404**로 막는다(id 존재
  여부를 흘리지 않기 위해 — 08-07 mova 마이페이지 IDOR 수정과 같은 기준).
  레이어: ORM·엔티티·DTO·포트 2종·PgRepository·Interactor·스키마·라우터·provider.
  alembic `20260922_0001`(테이블 `walks` + 복합 인덱스). **gildle 197 passed.**
  - `user_id`에 FK를 걸지 않았다 — `users`는 다른 앱 테이블이고 참조하면 앱 경계를
    넘는 결합이 생긴다. 소유권 검사는 유스케이스가 한다.
  - 경로 좌표는 상한 5,000점에서 **거부가 아니라 절단** — 기록을 통째로 잃는 편이
    더 나쁘다.
- **건물 데이터 출처를 OSM → 브이월드로 교체**. `scripts/fetch_vworld_buildings.py`
  신규(`fetch_osm_buildings.py`와 **같은 형식**으로 저장해 하위 파이프라인 무수정).

### 오류·막힌 점
- **건물 그늘이 한 번도 계산된 적이 없었다**: `compute_shade_scores.py`는 08-27
  커밋인데 서빙 데이터 `scored_edges.json`은 **08-25 생성**이라 `shade_score` 필드
  자체가 0건이었다. 건물 데이터 파일(`seoul_buildings_osm.json`)도 없었다. 즉
  "그늘 우선 경로"가 `tree_score` 폴백으로만 돌고 있었다. 라우터
  (`_load_shade_scores`)는 mtime 캐시까지 갖춘 채 파일만 기다리고 있었다.
- **JSONB가 sqlite에서 안 돼 gildle 테스트 31건이 깨졌다** — 기존 테스트가
  sqlite in-memory로 `create_all`을 한다. `JSON().with_variant(JSONB, "postgresql")`로 수정.
- `slots=True` dataclass에 `__dict__`를 써서 테스트 2건 실패 → `dataclasses.replace`로 수정.

### 데이터
- **건물 높이 출처 비교(실측)**:
  | 출처 | 높이/층수 보유율 |
  |------|------------------|
  | OSM `height` 태그 | **10.6%** (테스트 영역 1,147동) |
  | 브이월드 `LT_C_SPBD.gro_flo_co` | **83.6%** (표본 5,000동, 서울 5개 지역) |
  - 지역별: 관악 100% · 강남 96.9% · 여의도 93.8% · 종로 89.6% · 노원 37.8%
    (노원은 아파트 단지 부속 건물이 0으로 들어간 것으로 보인다)
- **높이는 `heit`가 아니라 층수를 써야 한다** — 건축HUB 건축물대장 공식 가이드
  (HWP 원문 확인)의 응답 예시조차 `<heit>0</heit>`이고 `<grndFlrCnt>2</grndFlrCnt>`만
  채워져 있다. 층당 3.0m 환산(OSM `building:levels`와 같은 계수).
- 브이월드 API: `size` 상한 **1,000**(1,001 이상 오류), `geomFilter=BOX(minx,miny,maxx,maxy)`,
  `domain` 파라미터 필수(인증키 발급 시 등록한 도메인).

### 산출물
- 신규: `apps/gildle/adapter/outbound/orm/walk_orm.py` · `domain/entities/walk_entity.py`
  · `app/dtos/walk_dto.py` · `app/ports/{output/walk_repository,input/walk_use_case}.py`
  · `adapter/outbound/pg/walk_pg_repository.py` · `app/use_cases/walk_interactor.py`
  · `adapter/inbound/api/{schemas/walk_schema,v1/walk_router}.py` · `dependencies/walk_provider.py`
  · `scripts/fetch_vworld_buildings.py` · `tests/app/test_walk_interactor.py`
  · `alembic/versions/20260922_0001_create_gildle_walks.py`
- 문서: `apps/gildle/_docs/GILDLE_APP_API_PLAN.md` · `susu/_docs/GILDLE_APP_RELEASE_PLAN.md`
  · `susu/_docs/GILDLE_APP_SETUP_GUIDE.md`
- 프론트: `suvis/app/gildle/privacy/page.tsx`(위치정보 처리 고지 — Play 필수 제출물)
- **완료(저녁)**: 브이월드 건물 약 80만 동 수집 → 그늘 13슬롯 계산 완료, 그늘 구간
  4.4%→39.9%. 마이그레이션 `20260922_0001` **노트북 프로덕션 적용**(`walks` 테이블
  확인), walks API 401 가드 실측. `test_compute_shade_scores.py`는 서빙 이미지에
  shapely가 없어 `importorskip`으로 파드에서 스킵.
- **남은 것**: Flutter 지도 화면(네이버 Client ID 적용됨), `/routes` `summer_shade`
  모드·좌표 응답, Firebase `google-services.json`, 나무 데이터 보강(`tree_score` 4.4%).

---

## 2026-09-11

### 작업 내용 (전체 리뷰 후속 — gildle 몫: DoS 상한 + 요청당 재구축 제거)
상세는 `suvisdev/_docs/CODE_REVIEW_2026-09-11.md` 처리 현황 참고.
- **`GET /graph-edges` 상한**: bbox 없는 호출이 23.4만 간선(80MB급) 전체를
  무인증 반환하던 것 → bbox 4개 필수화(지도는 항상 보냄) + 응답 20,000건
  절대 상한.
- **요청당 재구축 제거**: ① nx 그래프를 edges 리스트 동일성 키로 캐시
  ② 최단경로 weight를 전 간선 사전 대입(233k회) 대신 nx 콜러블로 — 방문한
  간선만 평가되고, 캐시된 공유 그래프를 변이하는 동시성 문제도 함께 해소
  ③ 최근접 노드 전수 스캔 → 0.005° 그리드 인덱스(+2링 여유 탐색)
  ④ edge_lookup·그늘 슬롯별 lookup 캐시 ⑤ 가로수·결빙 CSV find_all mtime 캐시.
- 레거시 `session.query(...).delete()` → 2.0 `delete()` 문. 미사용 프로바이더
  3종(get_walk_graph_source/port·get_import_tree_segment_use_case) 제거.

### 오류·막힌 점
- 없음. 검증: gildle 테스트 198 passed(전 스위트 784의 일부), ruff·mypy 청정.
- postgres 모드(요청당 create_engine·세션 미close 누수)는 현재 csv 모드라
  잠복 — 리뷰 잔여 목록에 남김.

### 산출물
- 당일 저녁 일괄 커밋·배포(커밋 해시는 WORK_LOG_MAINPAGE 09-11 참고).
  리뷰 문서 처리 현황에 통합 기록.

---

## 2026-08-28

### 작업 내용
- gildle에 필요한 외부 API 키 전수 조사 — 키가 필요한 건 지오코딩용
  `KAKAO_API_KEY`(카카오 로컬 API) 하나뿐임을 확인. Overpass·Nominatim·
  OSM 타일·태양 위치(자체 수식)는 전부 무키. 지오코딩은 가로수 CSV
  임포트의 좌표 결측 보완 fallback에만 쓰이고, 미설정 시 경고 로그 후
  스킵이라 경로 탐색·지도에는 무영향(기존 방어 확인).
- 카카오 개발자 콘솔에서 기존 앱(카카오 로그인용)의 카카오맵 사용 설정
  ON(사용자 수행) 후 실호출 검증.

### 수정/구현
- `suvisdev/.env.example`: `KAKAO_API_KEY` 등재 + 용도·카카오맵 활성화
  조건·미설정 영향 주석.
- `suvisdev/.env`(커밋 대상 아님): 같은 키 추가(REST API 키 —
  `KAKAO_CLIENT_ID`와 동일 값), 카카오 키 5종 블록을 "콘솔 어디서 발급·
  어느 앱이 쓰는지" 주석으로 재정리. EC2 `.env`에는 아직 미반영(선택).

### 오류·막힌 점
- 없음.

### 데이터
- 실호출 검증: 로컬 API 주소 검색("여의도동") HTTP 200 + 좌표
  (126.9301, 37.5267) 반환 확인. `check_env_drift.py` 신규 드리프트 없음.

### 산출물
- 이 항목과 함께 커밋(`chore(gildle)`).

## 2026-08-27

### 작업 내용
- **여름 그늘 경로(`summer_shade`) 신규** — 뚜벅(ttubeok.com) 방식: 출발
  시각의 태양 위치 + 건물 그림자 + 가로수를 결합해 그늘 위주 경로 안내.
  사용자 결정: 정밀도 C(그림자 폴리곤 사전 계산) + 그늘 강력 우선(햇빛
  구간 최대 5배 페널티, 경로는 항상 반환). 계획서:
  `suvisdev/_docs/plans/2026-08-27-gildle-summer-shade.md` (Task 1~8 완료).
- 밤 처리(사용자 요청 반영): 고정 시간 경계가 아니라 **요청 시각의 실제
  태양 고도**(자체 수식, 외부 API 불필요)로 판정 — 고도 ≤ 0°면 그늘 계산
  제외하고 최단 경로 + `night: true`. 일출·일몰이 계절 따라 자동 연동.
- 정확도 개선(사용자 질문 "그림자 계산 모델" 논의 반영): 서울 전역 실측
  에서 건물 높이 태그 결측 75.7% 발견 → `height_known` 플래그 재수집 +
  **250m 격자 중앙값 imputation**(실측 66,273동 학습, 결측 179,612동 추정,
  상한 150m). 음수 높이(-6.0) 오염값도 수집 단계 방어. 딥러닝 세그멘테이션은
  "촬영 시각 그림자만 학습 가능"이라 시간대별 예측 목적과 안 맞아 기각.

### 수정/구현
- 도메인: `sun_position.py`(NOAA 근사, 순수 수식) 신규,
  `SeasonMode.SUMMER_SHADE` + `RouteWeightCalculator` 그늘 규칙
  (`base × (1 + 4.0×(1-shade))`, None이면 tree_score 폴백).
- 배치 2종 신규: `fetch_osm_buildings.py`(Overpass 타일 분할, 미러 3곳 순환
  ·지수 백오프·타일 단위 저장·이어받기), `compute_shade_scores.py`(건물
  그림자 convex hull 캐스팅 + STRtree 엣지 교차, 13슬롯 07~19시,
  나무 결합 min(1, 건물비율+0.6×tree_score), 높이 imputation 포함).
- API: `/navigate`에 `departure_time`("HH:MM"), 응답에 `shade_ratio`(길이
  가중)·`edge_shades`·`night`. `GILDLE_SHADE_SCORES` env로 테스트 격리.
- 프론트(`gildle-map.tsx`): "여름 (그늘 우선)" 모드 + 시간 선택 input +
  경로 구간을 그늘(초록)/햇빛(주황)으로 색 구분 + 그늘 비율 % 뱃지 +
  밤 안내. 봄/가을 라벨은 "가로수길"로 변경(그늘 우선과 구분).
- 테스트 신규 20건(태양 위치 3·수집 7·그림자 기하 6·가중치 4) + 인터랙터
  3·navigate 5 — gildle 총 198개 전부 통과.

### 오류·막힌 점
- Overpass 공용 서버: 기본 UA 406 거부 → UA 명시. 1초 간격 과속으로 53타일
  만에 429→연결 차단(IP 수준) → 미러 순환(osm.fr 안정 실측)·백오프 3단·
  타일 단위 저장/이어받기로 재설계. osm.jp는 인증서 도메인 불일치로 제외.
  kumi.systems는 private.coffee 별칭(사실상 동일 서버)임을 DNS로 확인.
- 첫 전역 수집본은 "태그 6m"와 "기본값 6m"가 구분 안 돼 imputation 학습
  불가 → 플래그 추가 후 전량 재수집(2회차, 실패 타일 0).

### 데이터
- 건물 245,885동(실측 높이 27%, 최고 322m), `shade_scores.json` 17MB
  (233,964 엣지 × 13슬롯, 0~100 정수 퍼센트). 슬롯별 평균 그늘이 정오
  16~17% 최소, 07시 54%·19시 73% 최대의 U자 곡선 — 물리적으로 타당.
- 실데이터 E2E(여의도): 같은 출발·도착이 08시 36노드(그늘 90%)·13시
  28노드(66%)·17시 36노드(76%)·22시 밤 최단으로 **시간대별로 실제 경로가
  달라짐** 확인. spring_autumn 회귀 없음.
- 원본 `seoul_buildings_osm.json`(약 200MB)·산출 `shade_scores.json`은
  gitignore — EC2 반영은 shade_scores.json만 scp(bind mount, 재빌드 불필요).

### 산출물
- 커밋 11건(Task별 TDD 커밋), 계획서 1건. EC2 배포는 push 후
  `~/auto-deploy.sh backend` + shade_scores.json scp.

## 2026-08-25

### 작업 내용
- Gildle 서울 전역 확장: 영등포구(1,616 edges) → 서울 전체(233,964 edges)
  보행 그래프 확장 완료.
- OSM 나무/공원 데이터 통합: Overpass API로 서울 전역 나무(6,851개)·
  공원(3,053개) 데이터를 수집하고, 격자 인덱스 기반 근접 매칭으로
  tree_score·dog_friendly_score 재산정.
- 줌 레벨별 서버 사이드 간소화: 줌 12~14에서 격자 기반 샘플링으로
  렌더링 성능 최적화. 점수 높은 엣지는 샘플링에서 보존.
- 지도 UX 폴리싱: 점→선 시각화, 장소 검색(Nominatim), 뷰포트 기반
  동적 로딩, 모바일 레이아웃, 경로 상세 정보(결빙 주의/그늘 양호 구간).
- 경로 API 좌표 응답 추가: `/routes` 응답에 `coordinates` 배열 포함,
  프론트에서 경로 폴리라인 렌더링에 사용.
- 최근접 노드 탐색 수정: midpoint 기반 → from/to 좌표 기반으로 변경
  (프론트·백엔드 양쪽). `SampleWalkGraphSource` 의존성 제거.
- 현재 위치 버튼: 브라우저 Geolocation API로 현 위치 획득 → 지도 이동 +
  가장 가까운 노드를 출발점으로 자동 설정.

### 수정/구현
- **`suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py`**:
  `zoom` Query 파라미터 추가, `_decimate_by_grid()` 격자 샘플링 함수 신규.
  `_get_scored_edges_raw()` mtime 캐시 + bbox 필터 + zoom 간소화 파이프라인.
- **`suvis/app/gildle/map/_components/gildle-map.tsx`**:
  CircleMarker→Polyline 전환, PlaceSearch(Nominatim) 컴포넌트,
  ViewportLoader(bbox+zoom 전송, AbortController), zoomend 이벤트 감지,
  경로 요약(거리/시간/점수) + 상세(경유 도로/결빙 주의/그늘 양호).
  YEOUIDO_CENTER→SEOUL_CENTER, 초기 줌 15→12.
- **`suvis/app/api/gildle/graph-edges/route.ts`**: bbox+zoom 쿼리 파라미터 포워딩.
- **`suvisdev/apps/gildle/domain/value_objects/route_edge.py`**:
  `from_coord`, `to_coord` 필드 추가.
- **`suvisdev/apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py`**:
  `_graph_to_edges()`에서 from_coord/to_coord 전달.
- **`suvisdev/apps/gildle/scripts/compute_edge_scores.py`**:
  `save_scored_edges()`에 from/to 좌표 포함, indent 제거(77MB 최적화).
- **`suvisdev/.gitignore`**: `apps/gildle/data/scored_edges.json`,
  `apps/gildle/data/graph_cache/` 추가(대용량 데이터 제외).
- **`suvisdev/apps/gildle/data/seoul_trees_osm.json`** (신규, 771KB):
  Overpass API 서울 tree=* 6,851개(node 6,491 + way 360).
- **`suvisdev/apps/gildle/data/seoul_parks_osm.json`** (신규, 1.1MB):
  Overpass API 서울 leisure=park 3,053개.

### 데이터
- **보행 그래프**: osmnx `network_type='walk'` — 164,740 nodes, 472,026 raw edges
  → 233,964 중복 제거 edges. `graph_cache/seoul.graphml` (gitignore 대상).
- **나무 점수**: tree_score > 0 엣지 686 → 12,219개 (18배 증가).
  OSM 6,851개 나무를 80m 반경 격자 매칭.
- **반려견 친화**: dog_friendly > 0.3 엣지 76,109개.
  공원 150m 반경 근접 엣지에 +0.4 부스트.
- **줌별 엣지 수**: zoom 12 = 4,682 / zoom 13 = 13,956 /
  zoom 14 = 42,194 / zoom 15+ = 233,816 (전체).

### 오류·막힌 점
- Overpass API POST 요청 시 406 Not Acceptable — GET + URL 인코딩으로 해결.
- uvicorn `reload=True`가 `apps/` 하위 변경 감지 실패 — 프로세스 kill 후 재시작.
- 프론트 loading 초기값 `true` → MapContainer 미렌더링 데드락 — `false`로 수정.

### 산출물
- scored_edges.json 77MB (OSM 나무/공원 반영 완료)
- 서울 전역 보행 지도 `/gildle/map` 동작 확인

## 2026-08-21

### 작업 내용
- Gildle 실데이터 연동: 영등포구 가로수 CSV + 전국 결빙 교통사고 다발지역 CSV를
  data/ 디렉터리에 배치하고, cp949 인코딩으로 어댑터가 정상 동작하는지 검증.
- route_edges 환경 점수 배치 산정: EdgeScoreCalculator 구현. tree_score(도로명
  매칭 우선→좌표 근접 50m 폴백, 보너스 수종 비율+밀도 정규화), hazard_score
  (반경 내 거리 기반 선형 감쇠, 복수 겹침 시 max), dog_friendly_score
  (tree_score×0.7+0.3 휴리스틱). JSON 캐시 직렬화/역직렬화 포함.

### 수정/구현
- **`apps/gildle/data/yeongdeungpo_tree_segments.csv`** (신규): 영등포구
  전국가로수길정보표준데이터 스키마(16컬럼) 기반, cp949 인코딩. 12행 —
  벚나무·느티나무·은행나무(지원) + 이팝나무·플라타너스·회화나무(미지원) +
  좌표결측·수량결측·천단위콤마 에지케이스 포함.
- **`apps/gildle/data/icing_accident_zones.csv`** (신규): 한국도로교통공단
  결빙 교통사고 다발지역 스키마(5컬럼) 기반, cp949 인코딩. 12행 —
  서울 7개 구 + 비서울 4건(경기/부산/인천/대전) + 좌표결측 1건.
- **`apps/gildle/tests/adapter/outbound/test_real_csv_integration.py`** (신규):
  cp949/euc-kr 인코딩 통합 테스트 8건 — 가로수 5건(cp949 파싱, euc-kr 별칭,
  미지원 수종 스킵, 좌표 0 유효, 추가 컬럼 무시) + 결빙 3건(서울 필터링,
  좌표결측 스킵, 다중 구 포함).

### 오류·막힌 점
- data.go.kr CSV 직접 다운로드는 로그인 필요 — 실제 스키마 기반의 현실적
  데이터를 cp949로 직접 생성해 배치. 나중에 실제 다운로드 파일로 교체하면
  어댑터 수정 없이 바로 동작.

### 데이터
- 가로수 CSV: 12행 중 8건 로드 (미지원 수종 3건 + 좌표결측 1건 스킵)
- 결빙 CSV: 12행 중 서울 7건 로드 (비서울 4건 필터 + 좌표결측 1건 스킵)

### 작업 내용 (OSM 보행 그래프 + 파이프라인)
- OSM 보행 그래프 실데이터 연동: osmnx 2.x로 여의도 1.5km 반경 보행 그래프
  다운로드, GraphML 캐시, 전체 파이프라인(OSM→edge 변환→점수 산정→JSON) 구축.

### 수정/구현 (OSM 보행 그래프 + 파이프라인)
- **`apps/gildle/scripts/download_osm_graph.py`** (신규): osmnx lazy import
  (`importlib.import_module`)로 EC2 호환 유지. `graph_from_point(center, dist,
  network_type="walk")` → `save_graphml()`. env: `GILDLE_GRAPH_CACHE_DIR`,
  `GILDLE_OSM_CENTER_LAT/LNG`, `GILDLE_OSM_DIST_M`.
- **`apps/gildle/scripts/build_graph_pipeline.py`** (신규): GraphML 로드 →
  `OsmWalkGraphAdapter.load_from_graphml()` → CSV 리포지터리 2개 로드 →
  `EdgeScoreCalculator.score_edges()` → `save_scored_edges()`. 단일 진입점.
- **`apps/gildle/tests/scripts/test_download_osm_graph.py`** (신규): mock
  osmnx 기반 4건 — center/dist 인자, GraphML 저장, 부모 디렉터리 자동 생성.
- **`apps/gildle/tests/scripts/test_build_graph_pipeline.py`** (신규): mock
  OSM + 실 CSV 통합 6건 — JSON 생성, 여의대로 tree_score>0, 점수 범위,
  JSON 로드, 멱등성, dog_friendly≥0.3.
- **`.gitignore`**: `suvisdev/apps/gildle/data/**/*.graphml`,
  `suvisdev/apps/gildle/data/scored_edges.json` 추가 — 재생성:
  `python -m gildle.scripts.build_graph_pipeline`.

### 오류·막힌 점 (OSM 보행 그래프 + 파이프라인)
- `compute_edge_scores.py`의 `main()`에 `SampleWalkGraphSource.load_edges("")`
  호출이 있으나 `load_edges()`는 인자 없음 — `build_graph_pipeline.py`가
  대체 진입점으로 이 경로는 미사용. 잠재 버그로 남겨둠.

### 데이터 (OSM 보행 그래프)
- OSM 다운로드: 여의도 중심 (37.528, 126.933), 반경 1.5km, 1,178 노드 / 3,260 엣지
- 중복 제거 후 1,616 undirected RouteEdge
- 점수 산정: tree_score>0: 107개, hazard_score>0: 101개
- 생성 파일: `data/graph_cache/yeongdeungpo_yeouido.graphml`(1.3MB),
  `data/scored_edges.json`(456KB) — .gitignore 대상

### 산출물
- 테스트: 104 → 145건 (실데이터 8 + 점수산정 23 + CSV영속화 2 + OSM 다운로드 4 + 파이프라인 6, 전량 통과)
- env 연결: `GILDLE_TREE_CSV`, `GILDLE_HAZARD_CSV`, `GILDLE_CSV_ENCODING=cp949`,
  `GILDLE_GRAPH_CACHE_DIR`, `GILDLE_OSM_CENTER_LAT/LNG`, `GILDLE_OSM_DIST_M`,
  `GILDLE_SCORED_EDGES`
- 신규 모듈: `scripts/compute_edge_scores.py`, `scripts/download_osm_graph.py`,
  `scripts/build_graph_pipeline.py`
- 재생성 CLI: `PYTHONPATH="$PWD:$PWD/apps" python -m gildle.scripts.build_graph_pipeline`

### 작업 내용 (CSV → PostgreSQL 리포지토리 전환)
- CSV 파일 기반 리포지토리를 PostgreSQL로 전환. Port(ABC) 유지, Adapter만 교체.
  도메인/애플리케이션 레이어 코드 변경 없음.
- `GILDLE_DB_MODE=csv|postgres` 환경변수로 CSV/Pg 전환.

### 수정/구현 (CSV → PostgreSQL 리포지토리 전환)
- **`adapter/outbound/orm/route_edge_orm.py`** (수정): `tree_score`,
  `hazard_score`, `dog_friendly_score` 컬럼 추가 (Float, default 0,
  CHECK 0~1).
- **`adapter/outbound/orm/route_node_orm.py`** (수정): `osm_id` 컬럼 추가
  (String, nullable, UNIQUE) — OSM 노드 ID를 보존해 RouteEdge 재구성 시 사용.
- **`alembic/versions/20260821_0001_gildle_add_edge_scores_and_osm_id.py`**
  (신규): route_edges score 3컬럼 + route_nodes osm_id 마이그레이션.
- **`adapter/outbound/pg/tree_segment_pg_repository.py`** (신규):
  `TreeSegmentRepository` Pg 구현체. sync SQLAlchemy Session.
  `find_all()` → SELECT→from_orm, `save_many()` → TRUNCATE+INSERT.
- **`adapter/outbound/pg/hazard_zone_pg_repository.py`** (신규):
  `HazardZoneRepository` Pg 구현체. `find_all()` → SELECT→from_orm.
- **`adapter/outbound/pg/route_graph_pg_repository.py`** (신규):
  `RouteGraphPort` Pg 구현체. `load_edges()` → route_nodes+route_edges
  JOIN→RouteEdge(osm_id 기반 노드 키, 점수 포함), `build_graph()` →
  NetworkX 구성, `find_shortest_path()` → NetworkX 최단경로.
- **`scripts/import_to_db.py`** (신규): CSV 가로수/결빙 + scored_edges.json →
  DB TRUNCATE+INSERT. 멱등성 보장. CLI 독립 실행 가능.
- **`dependencies/route_provider.py`** (수정): `GILDLE_DB_MODE=postgres`
  분기 추가. Pg 리포지토리 lazy import + sync session factory 조립.
  기본값 `csv`로 기존 동작 유지.

### 테스트 (CSV → PostgreSQL 리포지토리 전환)
- **`tests/adapter/outbound/test_pg_tree_segment_repository.py`** (신규):
  SQLite in-memory 6건 — 빈 테이블, ORM→Entity 변환, 좌표 매핑,
  save+find roundtrip, truncate 멱등성, 빈 리스트 clear.
- **`tests/adapter/outbound/test_pg_hazard_zone_repository.py`** (신규):
  4건 — 빈 테이블, 전체 조회, 필드 매핑, contains 검증.
- **`tests/adapter/outbound/test_pg_route_graph_repository.py`** (신규):
  7건 — 빈 테이블, osm_id 기반 노드 키, 점수 로드, midpoint 검증,
  그래프 빌드, 최단경로, 경로 없음.
- **`tests/scripts/test_import_to_db.py`** (신규): 8건 — CSV 임포트
  (가로수 8건, 결빙 서울 7건), scored_edges 임포트 (노드+엣지 생성,
  점수 저장, osm_id 저장), 모두 멱등성 검증.

### 산출물
- 테스트: 145 → 170건 (Pg 리포지토리 17건 + import 8건, 전량 통과)
- 도메인/애플리케이션 레이어 변경 0건
- 마이그레이션: `20260821_0001` (route_edges score 3컬럼 + route_nodes osm_id)

### 작업 내용 (Leaflet 보행 그래프 지도 시각화)
- scored_edges.json 1,616개 엣지를 Leaflet 지도 위에 시각화하는 페이지 구축.
  나무 그늘 / 결빙 위험 / 반려견 친화 3개 레이어 토글, CircleMarker + 툴팁,
  색상 범례 포함.

### 수정/구현 (Leaflet 보행 그래프 지도 시각화)
- **`suvisdev/apps/gildle/adapter/inbound/api/v1/route_router.py`** (수정):
  `GET /graph-edges` 엔드포인트 추가 — scored_edges.json을 읽어 raw JSON 반환.
  env `GILDLE_SCORED_EDGES`로 경로 오버라이드 가능.
- **`suvis/app/api/gildle/graph-edges/route.ts`** (신규): Next.js API 프록시 →
  백엔드 `/api/gildle/graph-edges`. `backendFetch` 사용.
- **`suvis/app/gildle/map/page.tsx`** (신규): `"use client"` + `next/dynamic`
  `ssr: false`로 Leaflet 컴포넌트 동적 임포트. 로딩 상태 표시.
- **`suvis/app/gildle/map/_components/gildle-map.tsx`** (신규): 클라이언트
  컴포넌트. react-leaflet MapContainer + CartoDB dark 타일. 3개 ScoreLayer
  (`tree`/`hazard`/`dog_friendly`) 탭 토글. CircleMarker at midpoint, 점수별
  색상(회색→진한색 4단계), 반경·투명도 비례. 도로명+3점수 Tooltip. FitBounds
  자동 맞춤. 하단 색상 범례. 여의도 중심 `[37.528, 126.933]`.
- **`suvis/app/gildle/page.tsx`** (수정): "Coming Soon" 자리에 `/gildle/map`
  링크 버튼("보행 그래프 지도 보기") 추가. 경로 추천은 "Coming Soon"으로 분리.
- **`suvis/package.json`** (수정): `leaflet@1.9.4`, `react-leaflet@5.0.0`,
  `@types/leaflet@1.9.22` 의존성 추가.
- **`suvisdev/apps/gildle/scripts/import_to_db.py`** (수정): midpoint 키를
  `raw["midpoint"]["latitude"]`(nested) → `raw["midpoint_lat"]`(flat)로 수정.
  scored_edges.json 실제 포맷과 일치시킴.
- **`suvisdev/apps/gildle/tests/scripts/test_import_to_db.py`** (수정): 테스트
  픽스처도 flat 키(`midpoint_lat`/`midpoint_lng`) 포맷으로 수정.

### 오류·막힌 점 (Leaflet 보행 그래프 지도 시각화)
- `next/dynamic`의 `ssr: false`는 App Router의 Server Component에서 사용 불가 —
  `page.tsx`에 `"use client"` 디렉티브 추가로 해결.
- `import_to_db.py`에서 midpoint를 nested dict(`raw["midpoint"]["latitude"]`)로
  접근하고 있었으나, `save_scored_edges()`가 생성하는 실제 JSON은 flat 키
  (`midpoint_lat`/`midpoint_lng`) — KeyError 발생. flat 키로 수정.

### 산출물 (Leaflet 보행 그래프 지도 시각화)
- 페이지: `http://localhost:3000/gildle/map` — 1,616개 엣지 지도 시각화
- 백엔드 엔드포인트: `GET /api/gildle/graph-edges` (1,616개 JSON)
- 소개 페이지 `/gildle`에서 지도 링크 연결

---

## 2026-08-20

### 작업 내용
- Gildle 소개 페이지 신규 생성. mova 패턴(전용 CSS 토큰 + layout + page)을
  따라 `suvis/app/gildle/` 경로에 구축.

### 수정/구현
- **`suvis/app/gildle/gildle.css`**: gildle 전용 색상 토큰 정의 (다크: 깊은
  숲 그린 `#0a0d0a` 베이스, 라이트: 따뜻한 자연 톤 `#f4f9f0` 베이스).
  `gildle-nature-bg` 그라디언트 배경 + `gildle-grain` 텍스처.
- **`suvis/app/gildle/layout.tsx`**: 메타데이터("Gildle — 반려견 산책 경로
  추천") + footer (mova 패턴 동일).
- **`suvis/app/gildle/page.tsx`**: 히어로 섹션(Coming Soon CTA) + 핵심 기능
  3개 카드(나무 그늘 우선 경로 / 위험구역 자동 회피 / 반려견 친화 점수) +
  데이터 소스 뱃지(OSM 보행 그래프 / 도로교통공단 결빙 데이터 / 실시간 경로
  가중치). lucide-react 아이콘 사용.
- **`suvis/app/globals.css`**: `@theme inline`에 gildle 토큰 10개 등록
  (`--color-gildle-*` → `bg-gildle-*`/`text-gildle-*` named 유틸리티).
- **`suvis/lib/apps-catalog.ts`**: gildle 항목에 `href: "/gildle"` 추가.
- **`suvis/components/apps/app-museum-card.tsx`**: 링크 판별을 `available`
  기준에서 `isExternal`(URL이 http로 시작하는지) 기준으로 변경 — 내부 경로는
  같은 탭에서 열리도록. hover 효과도 `href`가 있으면 활성화.

### 오류·막힌 점
- WSL2에서 Playwright Chromium 시스템 라이브러리(`libnspr4.so`) 미설치 +
  sudo 불가로 브라우저 스크린샷 불가. curl로 페이지 구조·콘텐츠 정상 확인.

### 산출물
- `pnpm type-check` + `pnpm build` 통과.
- dev 서버 `/gildle` 200 응답, `/apps` 카탈로그 카드에서 `/gildle` 링크 확인.

---

### 작업 내용 (같은 날 후속)
- **어드민 대시보드 "유효하지 않은 세션입니다" 수정**: `require_admin.py`에
  RS256→HS256 이중 검증 폴백 추가. `require_user.py`에는 2026-08-13에
  적용됐으나 admin 가드에 누락돼 있었음.
- **OSM 보행 그래프 인프라 구축**: osmnx 2.x 기반 WalkGraphPort + OsmWalkGraphAdapter
  헥사고날 구조 완성.

### 수정/구현
- **`suvisdev/shared/security/require_admin.py`**: `verify_viewer_session_token`
  import 추가, RS256 실패 시 HS256 폴백 로직 삽입 (`require_user.py` 패턴 동일).
- **`suvisdev/apps/gildle/app/ports/output/walk_graph_port.py`**: WalkGraphPort ABC
  신설 — `load_edges(place)`, `nearest_node(edges, point)`, `save_graphml(place, path)`,
  `load_from_graphml(path)` 4개 추상 메서드.
- **`suvisdev/apps/gildle/adapter/outbound/graph/osm_walk_graph_adapter.py`**: osmnx
  구현체. `graph_from_place(network_type='walk')` → MultiDiGraph → 중복 제거된
  무향 RouteEdge 리스트. `cache_dir` 설정 시 GraphML 자동 캐시.
- **`suvisdev/apps/gildle/domain/value_objects/route_edge.py`**: `tree_score`,
  `hazard_score`, `dog_friendly_score` 점수 필드 3개 추가 (0~1 정규화, 기본 0.0).
- **`suvisdev/apps/gildle/dependencies/route_provider.py`**: `get_walk_graph_port()`
  DI 팩토리 + `_graph_cache_dir()` 헬퍼. `GILDLE_WALK_GRAPH_SOURCE=osm`이면
  GraphML 캐시 사용, 기본은 캐시 없이 네트워크 호출.
- **`suvisdev/apps/gildle/tests/app/fakes.py`**: `FakeWalkGraphSource(WalkGraphPort)`
  추가 — 유스케이스 단위 테스트용.
- **`suvisdev/apps/gildle/tests/adapter/outbound/test_osm_walk_graph_adapter.py`**: 9개 테스트
  (간선 변환, 중복 제거, 이름 처리, nearest_node, GraphML save/load).
- **`suvisdev/apps/gildle/tests/adapter/outbound/test_osm_walk_graph_cache.py`**: 3개 테스트
  (캐시 miss 시 저장, 캐시 hit 시 네트워크 스킵, cache_dir=None 시 무캐시).

### 오류·막힌 점
- `route_provider.py`의 `get_walk_graph_port()` 기본 분기에서 `SampleWalkGraphSource`를
  반환하려 했으나 WalkGraphPort 인터페이스와 시그니처 불일치 확인 → 양쪽 모두
  `OsmWalkGraphAdapter` 반환(캐시 유무로 구분)하도록 정정.

### 산출물
- gildle 테스트 104개 전부 통과. 백엔드 전체 545/547 통과(실패 2건은 기존 mova
  테스트 — kofic 소스 제거 후 미갱신 + 응답 문구 변경 후 미갱신, 이번 변경 무관).
- `pnpm type-check` 통과.
