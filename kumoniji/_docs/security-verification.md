# 쿠모니지 계정 — 보안 검증 기록 (SECURITY.md 1·2절)

기준: 바탕화면 `타일게임_기획/기획문서_하네스/SECURITY.md` 검증 번호. 계획: `plans/2026-11-21-B-accounts.md`.
**미실행·미구현은 통과로 적지 않는다**(SECURITY 46). 마지막 실행: 2026-11-21, 서버 `pytest -q` 213 통과(실제 Postgres 16.10), 앱 `flutter test` 28 통과(+ 브라우저 `--platform chrome` 1),
로컬 실브라우저(chrome-headless-shell, CSP 차단 모드) 가입→메일 링크→비밀번호 설정→로그인→새로고침 유지→싱글 판 시작.

## 자동 하네스

| 검증 | 내용 | 테스트 | 상태 |
|---|---|---|---|
| 1 | 가입·인증: 같은 응답, 대소문자만 다른 동시 가입 1계정, 선점 계정을 주인이 회수, 미인증은 세션 없음, 인증 계정 주소로 가입하면 주인에게만 메일 | `tests/accounts/test_web.py::test_1_*` | 통과 |
| 2 | 비밀번호 정책(15~128자, 개인정보 포함 거부, HIBP k-익명성·패딩, 장애 시 로컬 목록 → 보류) | `test_passwords.py` | 통과 |
| 3 | 1회용 토큰: 해시만 저장, 원자적 소비(동시 소비 1번만 — 변이로 실패 확인), 새 요청이 이전 무효(동시 발급도 계정 행 잠금으로 마지막 것만 — 변이로 실패 확인), 인증 버전 결속 | `test_tokens.py` | 통과 |
| 4 | 열거·대입: 있는 계정/없는 계정 응답 본문·시간(중앙값 차 < 50ms) 같음, 6번째 실패부터 지연, IP 10회 실패 후 Turnstile(실패 쪽으로 닫힘, 웹만 — 앱은 IP 지연만) | `test_web.py::test_4_*`, `test_limits.py` | 통과 |
| 5 | 재설정: 30분, GET은 소비 안 함, 완료 시 전 세션 폐기·알림·자동 로그인 없음, 재사용 거부, 링크 원점 고정(Host 위조 무시) | `test_web.py::test_5_*` | 통과 |
| 6 | 주소 변경(최근 인증·새 주소 확인·연속 변경 시 옛 링크 무효)·새 기기 알림·보호 링크(탈취자가 비밀번호를 바꿔도 유효 — 변이로 실패 확인, 1회, 로그인·복원 권한 없음, 잠금) | `test_protect.py` | 통과 |
| 7 | MFA: 맞혀야 켜짐, MFA 전 세션은 게임 불가, 같은 코드 재사용 거부, 실패 지연, 켜기·끄기·재발급은 최근 인증 + 알림, 켜면 다른 기기 로그아웃 | `test_mfa.py` | 통과 |
| 8 | 복구 코드 1회 / 탈퇴: 최근 인증(비밀번호 또는 구글 auth_time 5분), 즉시 차단, 개인정보 파기(11-25부터 화폐 기록 wallets·ledger·daily 포함), 같은 주소 재가입은 새 계정, 백업 복원 뒤 재삭제(멱등) | `test_mfa.py::test_8_*`, `test_delete.py` | 통과 |
| 9 | 구글: PKCE S256·state·nonce, 서명 키·알고리즘·iss·aud·exp·nonce 위조 거부, 흐름 쿠키 없는 콜백 거부 | `test_google.py::test_9_*` | 통과 |
| 10 | 같은 이메일 자체 계정과 자동 병합 안 함, 연결은 최근 인증(구글에 다녀오는 사이 세션이 폐기되면 거부), 다른 계정에 묶인 sub 거부, 마지막 로그인 수단 해제 거부 | `test_google.py::test_10_*` | 통과 |
| 11 | 액세스 위조(키·none·만료·iss·aud·typ·리프레시를 액세스로) 거부, 리프레시 회전·재사용 시 전 세션 폐기(회전된 토큰은 30일 이력에 남겨 몇 번 전 토큰이든 감지, HTTP 경로에서 커밋까지, 단 30초 안 같은 세션의 재요청은 다른 탭의 동시 갱신으로 보고 409 — 새 토큰 없음), 유휴 30일·절대 만료 없음 | `test_sessions.py::test_11_*`, `test_web.py::test_11_*` | 통과 |
| 12 | 로그아웃·전체 로그아웃 즉시, 리프레시가 최근 인증을 늘리지 않음, DB 장애 시 401(실패 쪽으로 닫힘) | `test_sessions.py::test_12_*`, `test_web.py::test_12_*` | 통과 |
| 13 | 쿠키 `__Host-`·HttpOnly·Secure·SameSite=Lax·Path=/·Domain 없음 | `test_web.py::test_13_*` | 통과 |
| 23 | 다른 계정의 판 조회·수 두기 404, 판 생성 제한 계정별 | `tests/test_api.py` | 통과 |
| 25·27 | CSP(인라인 스크립트 금지·object/frame-ancestors none), X-Frame-Options, nosniff, Referrer no-referrer, API no-store, 메일 링크 화면도 같은 머리글 | `tests/test_api.py::test_security_headers_*`, 실브라우저(위반 0) | 통과 |
| 26 | 쿠키 요청은 Origin 일치 + 이중 제출 CSRF, 앱(Bearer)은 사용자 정의 머리글로 면제 | `test_web.py::test_26_*`, `test_app_client_*` | 통과 |

## 예외·미구현 (책임자: 운영자)

| 항목 | 지금 | 이유·대체 통제 | 다시 볼 때 |
|---|---|---|---|
| CSP `style-src 'unsafe-inline'` | 허용 | Flutter 엔진이 `<style>`을 직접 넣음. 스크립트 인라인은 금지 | 글꼴 자체 호스팅 때 |
| 글꼴 `fonts.gstatic.com` | 허용(fetch만) | 앱이 글꼴을 번들하지 않음. 스크립트가 아니라 주소를 못 읽고 Referer도 안 감. CanvasKit은 자체 호스팅 | 글꼴 번들 시 제거 |
| Turnstile | 코드·CSP 준비, 실브라우저에서 Cloudflare 시험 키로 표시·통과·로그인 확인. **운영 키 비어 있음** | 키가 없으면 IP 10회 실패 뒤 그 IP의 로그인이 막힘(실패 쪽으로 닫힘, 하루 조용하면 풀림) | **머지 전 사용자 작업**: Cloudflare Turnstile 위젯 생성 → `KUMONIJI_TURNSTILE_SITE`/`SECRET` |
| 휴대폰 앱 | 토큰을 메모리에만, 구글은 웹만, MFA 등록 QR 없음(키 직접 입력) | 앱은 아직 출시 전(웹만 운영). 서버의 앱용 API(`/google/app`, Bearer)는 있음 | 안드로이드 출시 전: Keystore 보관(flutter_secure_storage)·google_sign_in |
| 앱의 사람 확인 | 없음 — 앱 요청은 Turnstile 대신 IP·계정 지연(최대 15분)·분당 예산만 | 앱에 Turnstile 화면이 없어 공유 IP 사용자가 막히지 않게(Codex 지적) | 안드로이드 출시 전: Play Integrity 등 앱용 확인 |
| 기기 목록 화면 | API만(`/api/auth/sessions`) | 전체 로그아웃으로 대체 | 멀티 단계에서 계정 화면 보강 |
| 보호 잠금 풀기 | 운영자가 DB에서 `locked_at` 해제 | SECURITY 6 "별도 복구 절차" — 자동 복원 권한 없음이 요구사항 | 문의 창구 생기면 절차 문서화 |
| 새 기기 알림 내용 | "새 기기에서 로그인" + 보호 링크 | 대략 위치·기기 이름은 아직 | 다음 계정 보강 때 |
| 삭제 이력 | 같은 DB(`deletion_log`) | SECURITY 36의 독립 저장소는 백업 체계(6절, 범위 밖)와 같이 | 백업 설계 때 |
| 발신 도메인(31) | Gmail(아침 메일 계정) | 사용자 결정 — 도메인 사면 `KUMONIJI_MAIL_FROM` 교체 후 SPF·DKIM·DMARC | 도메인 구입 때 |
| Apple 로그인·토큰 취소 | 해당 없음 | 아이폰 미출시 | 아이폰 출시 때 |
