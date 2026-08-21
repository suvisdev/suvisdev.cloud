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

### 산출물
- 테스트: 104 → 135건 (실데이터 8건 + 점수산정 23건 + CSV영속화 2건, 전량 통과)
- env 연결: `GILDLE_TREE_CSV`, `GILDLE_HAZARD_CSV`, `GILDLE_CSV_ENCODING=cp949`
- 신규 모듈: `scripts/compute_edge_scores.py`(EdgeScoreCalculator + CLI + JSON 캐시)
- CLI: `PYTHONPATH="$PWD:$PWD/apps" python -m gildle.scripts.compute_edge_scores`

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
