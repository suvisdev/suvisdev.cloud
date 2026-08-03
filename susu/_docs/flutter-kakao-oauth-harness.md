# HARNESS — susu 카카오 모바일 로그인: 클라이언트 (Flutter)

> 이 문서는 susu(Flutter) 클라이언트 구현 범위만 다룬다. 백엔드(`apps/auth`) 검증/JWT
> 발급/Redis 네임스페이스 분리는 [`suvisdev/_docs/flutter-kakao-oauth-harness.md`](../../suvisdev/_docs/flutter-kakao-oauth-harness.md)를 본다.
> **이번 라운드는 문서 작성까지만 — 코드는 작성하지 않는다.**

## Goal
susu(Flutter)에 카카오 OAuth 로그인을 붙이되, **유저 검증과 JWT 발급은 클라가 하지 않고
전량 백엔드(`apps/auth`)에 위임**한다. 클라는 카카오 SDK로 access token만 얻어 백엔드로
전달하고, 백엔드가 내려준 자체 JWT(+refresh token)만 보관·사용한다.

## Context — 착수 전 확인 사항
- susu는 `kakao_flutter_sdk`를 쓴다. 단 **현재 `susu/pubspec.yaml`에는 `kakao_flutter_sdk`,
  HTTP 클라이언트(dio 등), secure storage 패키지가 전혀 없다** — 이번 작업에서 의존성부터
  추가해야 하는 그린필드 상태다.
- `susu/lib/`도 기본 Flutter 템플릿 상태이고 인증/로그인 관련 기존 코드가 없다. 참고할
  기존 관례가 없으므로, 화면/상태관리 스타일은 susu의 다른 기존 위젯 규칙(`susu/_docs/`)을
  따르되 이번 문서 범위 밖(Out of scope의 "UI 디자인/화면 플로우 세부" 참고).
- 백엔드 엔드포인트는 `POST /auth/kakao/mobile` (백엔드 문서 R2/R3 확정) — 요청 바디는
  `{ access_token }` 하나만 보낸다.

## Architecture (구현 대상 플로우 — 클라 관점)
```
[susu / Flutter]
  loginWithKakaoTalk() 또는 loginWithKakaoAccount()
    → OAuthToken(access token) 획득
    → ※ 클라에서 UserApi.instance.me() 호출 금지 (유저정보 조회는 백엔드가 단독 수행)
  POST /auth/kakao/mobile  { access_token }
    ← 백엔드가 access JWT + refresh token(+ nickname 등 표시정보) 응답
  access JWT / refresh token을 secure storage에 저장
```
(백엔드 내부 처리는 [백엔드 쪽 문서](../../suvisdev/_docs/flutter-kakao-oauth-harness.md) 참고.)

## Requirements

### R1. 클라이언트(susu) — 중복 요청 제거
- `loginWithKakaoTalk()`(카톡 설치 시) → 실패 폴백 `loginWithKakaoAccount()`.
- 로그인 결과에서 **access token만** 추출해 백엔드로 전송. **`me()`를 호출하지 않는다**
  (중복 유저정보 조회 방지 — 검증 출처는 백엔드가 호출하는 kapi 응답뿐이어야 함).
- 클라가 필요로 하는 유저 표시 정보는 백엔드 응답(JWT payload 또는 응답 body의 nickname
  등)에서 받는다.
- 백엔드가 준 access JWT를 secure storage에, refresh token도 secure storage에 저장.

## Constraints
- 새 로그인/토큰 관리 로직을 즉흥적으로 설계하지 말고, 백엔드 API 계약(`POST
  /auth/kakao/mobile` 요청/응답 스키마)이 확정된 뒤 그에 맞춰 구현한다 — 계약은
  [백엔드 쪽 문서](../../suvisdev/_docs/flutter-kakao-oauth-harness.md)가 단일 소스.
- 시크릿(카카오 native app key 등)은 하드코딩하지 말고 플랫폼별 설정 파일/환경 변수
  관례를 따른다. `.env`류를 커밋하지 말 것.
- 웹 로그인(suvis 프론트)과는 완전히 별개 구현 — 토큰 저장소·엔드포인트를 공유하지 않는다.

## Out of scope
- 네이버/구글 등 타 provider(이번엔 카카오만).
- OIDC(idToken) 방식 — 백엔드 문서 Appendix 참고, 채택 여부는 백엔드 쪽 결정에 종속.
- 프론트 UI 디자인/화면 플로우 세부(로그인 버튼 배치, 애니메이션 등).
- 백엔드 검증/JWT 발급/Redis 저장 — [백엔드 쪽 문서](../../suvisdev/_docs/flutter-kakao-oauth-harness.md) 참고.

## Verification Gates (클라 담당분)
1. **G1 클라**: susu에서 카카오 로그인 → 백엔드 JWT 수신까지 성공, 클라 코드에 `me()`
   호출이 없음(grep 확인).

(백엔드 쪽 게이트 G2~G4, 회귀 테스트는 [백엔드 쪽 문서](../../suvisdev/_docs/flutter-kakao-oauth-harness.md) 참고.)

## Deliverables
- `kakao_flutter_sdk`, HTTP 클라이언트, secure storage 의존성 추가(pubspec.yaml).
- susu 카카오 로그인 서비스(access token만 전송, 백엔드 응답의 JWT/refresh token 저장).
- 작업 로그: `_docs/WORK_LOG.md`에 요약 기록(susu 관련 작업 로그 위치는 저장소
  루트 `CLAUDE.md` 문서 배치 규칙 참고).
