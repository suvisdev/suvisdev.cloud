# gildle 앱 출시용 API 설계 (2026-09-22)

앱 출시를 **gildle만** 하기로 한 결정(2026-09-22)에 따른 백엔드 작업 목록.
mova를 빼는 이유는 TMDB 약관의 AI 학습 조항(별도 서면 계약 필요)이고,
gildle은 OSM 데이터와 자체 계산만 쓰므로 그 리스크가 없다.

## 현황 실측 (2026-09-22)

| 항목 | 상태 |
|------|------|
| 라우터 | `route_router.py` 하나 — 엔드포인트 4개 |
| 엔드포인트 | `POST /routes` · `POST /navigate` · `GET /graph-edges` · `GET /map-data` |
| 인증 | **없음** — 전부 공개, `require_user` 미적용 |
| DB | `route_nodes`·`route_edges`·`tree_segments`·`route_requests`·`route_results` **전부 0행** |
| 데이터 원천 | 파일 — `data/scored_edges.json` **76MB**를 프로세스 메모리로 로드 |
| 사용자 기능 | **0개** (저장·기록·즐겨찾기·통계 전부 없음) |
| 웹 화면 | `app/gildle/page.tsx`, `app/gildle/map/page.tsx` 2개 |

즉 현재 gildle은 **stateless 경로 계산기**다. 앱으로 내려면 "사용자가 돌아올
이유"에 해당하는 상태 저장이 통째로 없다.

---

## 1. 반드시 필요한 것 (앱 출시 최소선)

### 1-1. 인증 연동 — 기존 자산 재사용
카카오 OAuth·JWT·refresh token은 `apps/auth`에 이미 있고 susu가 쓰고 있다.
gildle 라우터에 **선택적 인증**(`optional_user`)을 붙인다 — 비로그인도 경로
계산은 되게 두고, 저장 계열만 `require_user`로 막는다. 웹(비로그인 사용)이
깨지지 않게 하는 것이 조건이다.

### 1-2. 산책 기록 (핵심 — 앱의 존재 이유)
```
POST   /gildle/walks            산책 시작·종료 기록 저장   require_user
GET    /gildle/walks            내 산책 목록(페이지네이션) require_user
GET    /gildle/walks/{id}       상세(경로 폴리라인 포함)   require_user
DELETE /gildle/walks/{id}       삭제                       require_user
```
저장 필드: 시작·종료 시각, 거리(m), 소요(초), 경로 폴리라인, 계절 모드,
평균 그늘 점수. **위치 데이터는 개인정보**이므로 보존 기간·삭제 절차를
개인정보처리방침에 명시해야 한다(아래 §4).

### 1-3. 즐겨찾기 경로
```
POST   /gildle/favorites        경로 저장(이름 지정)  require_user
GET    /gildle/favorites        목록                  require_user
DELETE /gildle/favorites/{id}   삭제                  require_user
```

### 1-4. 현재 위치 기반 추천 — 모바일 필수
```
GET /gildle/nearby?lat=&lon=&radius=&mode=   주변 추천 경로 N개
```
웹은 지도에서 출발·도착을 찍지만, 앱은 "지금 여기서 걷기 좋은 길"이 자연스럽다.
현행 `POST /routes`는 출발·도착을 모두 요구하므로 그대로는 못 쓴다.

### 1-5. 앱 플랫폼 API (mova·gildle 공통, `core`에 두는 편이 낫다)
```
GET /app/version?platform=android   최소 지원 버전·강제 업데이트 여부
POST /app/push-tokens               FCM 토큰 등록 (푸시를 쓸 경우)
```
현재 저장소에 `fcm`·`device_token`·`app_version` 관련 코드는 **하나도 없다**.
푸시가 당장 필요 없다면 `version`만 먼저 만들어도 된다 — 강제 업데이트 수단이
없으면 구버전 앱이 API 변경 때 깨진 채로 남는다.

---

## 2. 있으면 좋은 것 (2차)

```
GET  /gildle/stats              누적 거리·횟수·이번 달 요약   require_user
POST /gildle/walks/{id}/share   경로 공유 링크 생성
GET  /gildle/routes/recent      최근 계산한 경로(재실행용)
```
`route_requests`·`route_results` ORM이 이미 있으나 **0행이고 어디서도 쓰이지
않는다**(스키마 테스트에만 등장). 최근 경로를 살리려면 이 테이블을 실제로
채우는 것부터다.

---

## 3. 기술 과제 (앱 트래픽 전에 정리)

### 3-1. 76MB JSON 메모리 로드
`_load_scored_edges()`가 `data/scored_edges.json`(76MB)을 프로세스 메모리에
올린다. 파드 재시작마다 로드하고, 워커를 늘리면 그만큼 복제된다. 앱 사용자가
붙기 전에 **DB(PostGIS 또는 기존 `route_edges` 테이블)로 이전**하는 편이 낫다.
테이블은 이미 만들어져 있고 0행이다 — 설계는 있고 적재만 안 된 상태다.

### 3-2. 서비스 범위
2026-08-25 기준 **서울 전역**만 지원한다. 스토어 설명에 지역 한정을 명시하지
않으면 다른 지역 사용자에게 "동작하지 않는 앱"이 된다.

### 3-3. 백엔드 가용성
API는 노트북 k3s + Cloudflare 터널이다. 노트북이 꺼지면 앱이 전부 실패한다.
심사 중 리뷰어가 접속하는 시점에 꺼져 있으면 거절 사유가 된다. 출시 전에
상시 가동 여부를 정해야 한다(클라우드 이전 또는 노트북 상시 운영).

---

## 4. 법적·정책 항목 (Play Console 제출물)

- **위치 정보 처리 고지** — gildle은 위치를 다루므로 개인정보처리방침에
  수집 항목·목적·보존 기간·삭제 절차를 명시해야 한다. mova 쪽 방침
  (`suvis/app/mova/privacy/page.tsx`)과 **별도 문서**가 필요하다.
- **데이터 보안 양식** — 위치 수집 여부, 전송 암호화, 삭제 요청 경로를 신고한다.
- **OSM 데이터 저작자 표시** — gildle은 OpenStreetMap 기반이다(`seoul_parks_osm.json`,
  `seoul_trees_osm.json`). 웹 지도에는 이미 있다(`gildle-map.tsx:765`의 Leaflet
  `attribution`). **앱에는 새로 넣어야 한다** — 지도 화면에 "© OpenStreetMap
  contributors" 고지.
- TMDB는 gildle과 무관하다 — mova 웹에만 적용된다.

---

## 작업 순서 제안

1. 선택적 인증 도입 준비 — 아래 2번의 전제
2. 선택적 인증 도입 + `walks` 테이블·API
3. `nearby` 엔드포인트
4. `scored_edges.json` → DB 이전
5. `app/version` API
6. 통계·공유 (2차)
